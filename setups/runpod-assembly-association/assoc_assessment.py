"""
Substep 7 assessment video (iteration 64): a 3D view of the reservoir in which the user can judge
whether the association formed.

AssessmentRecorder takes the place of AssocVideo in AssocRun.run() (`video.kind` "assessment"). Per
frame it keeps A_g of every group and the phase header; at every phase change it stores the
permanent weights that changed since the last change (sparse, on the CPU). write() selects the
synapses with the largest final change of w_perm against the initial weights, rebuilds their change
over the frames, saves everything to an .npz and renders the .mp4 with render().

render() draws with NumPy + Pillow (no EGL, like assoc_video.py): neurons as points coloured by the
A_g of their group, A / B / C circled, the selected synapses as lines (pre -> post) coloured by their
permanent change, A_g traces of A, B and C, and a phase timeline with a moving playhead. The view
turns slowly around the vertical axis. Lines are drawn with Pillow instead of the VisPy LineVisual
the task names (same content, one colour per synapse; no GL context needed on the pod).
"""

from __future__ import annotations

import numpy as np
import torch
from PIL import Image, ImageDraw

PHASES = [  # (key, label, colour); matched against the header and the step within the phase
    ("gap", "gap", (70, 74, 90)),
    ("joint", "joint activation", (60, 160, 230)),
    ("c1test", "C1-phase test (A alone)", (150, 120, 220)),
    ("c2", "short circuit stage (C2)", (240, 150, 40)),
    ("final", "final test (A alone, then B alone)", (60, 220, 120)),
]
PHASE_INDEX = {k: i for i, (k, _, _) in enumerate(PHASES)}
MARK_COLORS = {"A": (60, 230, 110), "B": (255, 150, 40), "C": (60, 200, 255)}


def phase_of(header: str, inject_steps: int) -> int:
    """Phase of a frame from its header, "<phase>  step <i>/<n>  t=<t>" as AssocRun.run() writes it."""
    base, _, rest = header.partition("  step ")
    step = int(rest.split("/")[0]) if rest[:1].isdigit() else 0
    injecting = step < inject_steps
    if "final" in base:
        return PHASE_INDEX["final"]
    if "C2 round" in base:
        return PHASE_INDEX["c2"] if injecting else PHASE_INDEX["gap"]
    if "C1 round" in base:
        return PHASE_INDEX["joint"] if injecting else PHASE_INDEX["gap"]
    if "test" in base:
        return PHASE_INDEX["c1test"]
    return PHASE_INDEX["gap"]


class AssessmentRecorder:

    def __init__(self, run, marks: dict, n_lines: int = 1500):
        self.run = run
        self.marks = {k: int(g) for k, g in marks.items()}
        self.n_lines = int(n_lines)
        self.inject_steps = int(run.p["inject_steps"])
        self.a_g: list[np.ndarray] = []
        self.headers: list[str] = []
        self.phase: list[int] = []
        self.w0 = run.P.w_perm.clone()
        self.w_last = self.w0.clone()
        self.diffs: list[tuple[int, np.ndarray, np.ndarray]] = []   # (frame, flat index, new value)
        self._base = None

    def _snapshot(self):
        w = self.run.P.w_perm
        idx = torch.nonzero((w != self.w_last).view(-1)).view(-1)
        if len(idx):
            self.diffs.append((len(self.a_g), idx.cpu().numpy(), w.view(-1)[idx].cpu().numpy()))
            self.w_last = w.clone()

    def add(self, a_g: np.ndarray, c1, c2, header: str):
        base = header.partition("  step ")[0]
        if self._base is not None and base != self._base:   # phase change (not every frame)
            self._snapshot()
        self._base = base
        self.a_g.append(np.asarray(a_g, dtype=np.float16))
        self.headers.append(header)
        self.phase.append(phase_of(header, self.inject_steps))

    def write(self, path: str, fps: int = 30) -> int:
        if not self.a_g:
            return 0
        self._snapshot()
        run, eng = self.run, self.run.eng
        dw = (run.P.w_perm - self.w0).view(-1)
        k = min(self.n_lines, int((dw.abs() > 1e-6).sum()))
        sel = torch.topk(dw.abs(), k).indices if k > 0 else torch.zeros(0, dtype=torch.long, device=dw.device)
        n = eng.N
        pre = (sel % n)
        post = run.P.post.view(-1)[sel]
        sel_np = sel.cpu().numpy()
        # change of each selected synapse over the frames (piecewise constant between snapshots)
        w0_sel = self.w0.view(-1)[sel].cpu().numpy()
        pos_in_sel = {int(s): j for j, s in enumerate(sel_np)}
        cur = w0_sel.copy()
        snap_frames, snap_dw = [0], [np.zeros(k, dtype=np.float32)]
        for frame, idx, val in self.diffs:
            hit = [(pos_in_sel[int(i)], v) for i, v in zip(idx, val) if int(i) in pos_in_sel] if k else []
            for j, v in hit:
                cur[j] = v
            snap_frames.append(frame)
            snap_dw.append((cur - w0_sel).astype(np.float32))
        pos = eng.pos.cpu().numpy() / np.asarray(eng.reservoir_shape, dtype=np.float32)
        data = dict(
            a_g=np.stack(self.a_g), phase=np.asarray(self.phase, dtype=np.int8),
            headers=np.asarray(self.headers), pos=pos.astype(np.float16),
            groups=eng.groups.cpu().numpy().astype(np.int32),
            mark_names=np.asarray(list(self.marks)), mark_groups=np.asarray(list(self.marks.values())),
            group_centroid=(eng.group_centroid.cpu().numpy() / np.asarray(eng.reservoir_shape)).astype(np.float32),
            pre=pre.cpu().numpy(), post=post.cpu().numpy(),
            snap_frames=np.asarray(snap_frames), snap_dw=np.stack(snap_dw).astype(np.float16),
            fps=np.asarray(fps), inject_steps=np.asarray(self.inject_steps))
        npz = path.rsplit(".", 1)[0] + ".npz"
        np.savez_compressed(npz, **data)
        return render(npz, path)


def _heat(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return (np.stack([np.clip(3 * x, 0, 1), np.clip(3 * x - 1, 0, 1), np.clip(3 * x - 2, 0, 1)], -1) * 255)


def _dw_colour(v: np.ndarray, vmax: float) -> np.ndarray:
    """Positive change: dark blue -> cyan -> white; negative: magenta."""
    x = np.clip(np.abs(v) / max(vmax, 1e-9), 0.0, 1.0)
    pos = np.stack([np.clip(2 * x - 1, 0, 1), np.clip(1.6 * x, 0, 1), 0.45 + 0.55 * x], -1)
    neg = np.stack([0.5 + 0.5 * x, 0.15 + 0.2 * x, 0.6 + 0.4 * x], -1)
    return (np.where((v >= 0)[:, None], pos, neg) * 255).astype(np.uint8)


def _project(p: np.ndarray, angle: float, elev: float, cx: float, cy: float, scale: float) -> np.ndarray:
    q = p - 0.5
    c, s = np.cos(angle), np.sin(angle)
    x = c * q[:, 0] + s * q[:, 1]
    y = -s * q[:, 0] + c * q[:, 1]
    ce, se = np.cos(elev), np.sin(elev)
    z = q[:, 2]
    return np.stack([cx + scale * x, cy - scale * (ce * z - se * y)], -1)


def render(npz_path: str, mp4_path: str, width: int = 1280, height: int = 720,
           png_frames: list[int] | None = None) -> int:
    """Writes the .mp4; with `png_frames`, writes only those frames as <mp4_path stem>_f<i>.png
    (a preview that needs no video encoder)."""
    d = np.load(npz_path, allow_pickle=False)
    a_g, headers = d["a_g"].astype(np.float32), d["headers"]
    inject_steps = int(d["inject_steps"]) if "inject_steps" in d else 50
    phase = np.asarray([phase_of(str(h), inject_steps) for h in headers], dtype=np.int8)
    pos, groups, cen = d["pos"].astype(np.float32), d["groups"], d["group_centroid"]
    marks = dict(zip([str(x) for x in d["mark_names"]], [int(x) for x in d["mark_groups"]]))
    pre, post = d["pre"], d["post"]
    snap_frames, snap_dw = d["snap_frames"], d["snap_dw"].astype(np.float32)
    n_frames = len(a_g)
    final = np.abs(snap_dw[-1]) if snap_dw.size else np.zeros(1)
    vmax = float(final.max()) if final.size else 1.0
    vmin = float(np.percentile(final[final > 0], 5)) if (final > 0).any() else 0.0
    corners = np.asarray([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], dtype=np.float32)
    edges = [(i, j) for i in range(8) for j in range(i + 1, 8) if bin(i ^ j).count("1") == 1]
    view_w, bar_h, side_w = 880, 70, width - 880
    view_h = height - bar_h
    cx, cy, scale = view_w / 2, view_h / 2 + 10, view_h * 0.62
    elev = np.radians(22.0)
    # timeline: one coloured cell per frame
    bar = np.zeros((bar_h - 30, width - 40, 3), dtype=np.uint8)
    cols = np.asarray([c for _, _, c in PHASES], dtype=np.uint8)
    xs = (np.arange(width - 40) * n_frames // (width - 40)).clip(0, n_frames - 1)
    bar[:] = cols[phase[xs]][None, :, :]
    marks_g = list(marks.items())
    if png_frames is None:
        import imageio
        writer = imageio.get_writer(mp4_path, fps=int(d["fps"]), codec="libx264", quality=8, pixelformat="yuv420p")
    trace_len = 600
    for f in (range(n_frames) if png_frames is None else [i for i in png_frames if 0 <= i < n_frames]):
        img = np.full((height, width, 3), 12, dtype=np.uint8)
        angle = np.radians(35.0) + 0.9 * np.pi * f / max(1, n_frames - 1)
        p2 = _project(pos, angle, elev, cx, cy, scale)
        act = a_g[f][groups]
        order = np.argsort(act)                         # active neurons drawn last
        xy = np.round(p2[order]).astype(int)
        ok = (xy[:, 0] >= 1) & (xy[:, 0] < view_w - 2) & (xy[:, 1] >= 1) & (xy[:, 1] < view_h - 2)
        a_o = act[order]
        col = np.where((a_o > 0.05)[:, None], _heat(0.35 + 0.65 * a_o), 48).astype(np.uint8)
        img[xy[ok, 1], xy[ok, 0]] = col[ok]
        for lim, offs in ((0.2, ((1, 0), (0, 1), (1, 1))),                 # firing groups: 2 px
                          (0.5, ((-1, 0), (0, -1), (2, 1), (1, 2), (-1, -1)))):  # active: about 3 px
            m = ok & (a_o >= lim)
            for dx, dy in offs:
                img[xy[m, 1] + dy, xy[m, 0] + dx] = col[m]
        frame = Image.fromarray(img)
        dr = ImageDraw.Draw(frame)
        cp = _project(corners, angle, elev, cx, cy, scale)
        for i, j in edges:
            dr.line([tuple(cp[i]), tuple(cp[j])], fill=(70, 74, 92), width=1)
        # permanent changes so far
        s = int(np.searchsorted(snap_frames, f, side="right")) - 1
        dw = snap_dw[max(s, 0)]
        m = np.abs(dw) > 0.02 * vmax
        if m.any():
            a = _project(pos[pre[m]], angle, elev, cx, cy, scale)
            b = _project(pos[post[m]], angle, elev, cx, cy, scale)
            mag = np.clip((np.abs(dw[m]) - vmin) / max(vmax - vmin, 1e-9), 0.0, 1.0)
            lc = _dw_colour(np.sign(dw[m]) * (0.15 + 0.85 * mag), 1.0)
            for j in np.argsort(np.abs(dw[m])):
                dr.line([tuple(a[j]), tuple(b[j])], fill=tuple(int(v) for v in lc[j]), width=1)
        for name, g in marks_g:
            c = _project(cen[g][None, :], angle, elev, cx, cy, scale)[0]
            r = 0.075 * scale
            dr.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=MARK_COLORS.get(name, (255, 255, 255)), width=2)
            dr.text((c[0] + r + 3, c[1] - r), name, fill=MARK_COLORS.get(name, (255, 255, 255)))
        # side panel: A_g traces of A, B, C
        x0, y0, pw, ph = view_w + 20, 60, side_w - 40, 220
        dr.rectangle([x0, y0, x0 + pw, y0 + ph], outline=(80, 84, 100))
        y_half = y0 + ph - 0.5 * ph
        dr.line([(x0, y_half), (x0 + pw, y_half)], fill=(60, 64, 78))
        lo = max(0, f - trace_len)
        for k, (name, g) in enumerate(marks_g):
            v = a_g[lo:f + 1, g]
            if len(v) > 1:
                px = x0 + np.arange(len(v)) * pw / trace_len
                py = y0 + ph - v * ph
                dr.line(list(zip(px.tolist(), py.tolist())), fill=MARK_COLORS.get(name, (255, 255, 255)), width=2)
            dr.text((x0 + 6 + 40 * k, y0 + ph + 8), f"{name} {a_g[f, g]:.2f}", fill=MARK_COLORS.get(name, (255, 255, 255)))
        dr.text((x0, y0 - 18), "A_g of A, B, C (line: active at 0.5)", fill=(210, 210, 210))
        # legend
        ly = y0 + ph + 40
        dr.text((x0, ly), "points: neurons, colour = A_g of their group", fill=(200, 200, 200))
        dr.text((x0, ly + 18), f"lines: {len(pre)} synapses with the largest", fill=(200, 200, 200))
        dr.text((x0, ly + 34), f"permanent change, blue -> white: {vmin:.2f} to {vmax:.2f}", fill=(200, 200, 200))
        for k, (_, lab, c) in enumerate(PHASES):
            dr.rectangle([x0, ly + 64 + 18 * k, x0 + 12, ly + 76 + 18 * k], fill=c)
            dr.text((x0 + 18, ly + 63 + 18 * k), lab, fill=(200, 200, 200))
        # header and timeline with playhead
        dr.text((12, 10), f"{headers[f]}   [{PHASES[int(phase[f])][1]}]   frame {f + 1}/{n_frames}", fill=(235, 235, 235))
        frame_np = np.asarray(frame).copy()
        frame_np[view_h + 15:view_h + bar_h - 15, 20:width - 20] = bar
        xp = 20 + int(f * (width - 40) / max(1, n_frames - 1))
        frame_np[view_h + 8:view_h + bar_h - 8, max(0, xp - 1):xp + 2] = 255
        if png_frames is None:
            writer.append_data(frame_np)
        else:
            Image.fromarray(frame_np).save(f"{mp4_path.rsplit('.', 1)[0]}_f{f}.png")
    if png_frames is None:
        writer.close()
    return n_frames
