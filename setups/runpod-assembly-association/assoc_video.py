"""
Video panel for the assembly association task: A_g(t) as a heat map over the location-group
grid (one tile per z-layer of groups), active assemblies outlined, A / B / C marked, and
C1 / C2 maximum projections along z. Pure NumPy + Pillow frames, written with imageio/ffmpeg;
no EGL needed, so metrics pods and video pods share one environment.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

ACTIVE_THRESHOLD = 0.5
MARK_COLORS = {"A": (60, 230, 110), "B": (255, 150, 40), "C": (60, 200, 255)}


def _heat(x: np.ndarray) -> np.ndarray:
    """Black -> red -> yellow -> white colormap for x in [0, 1]; returns uint8 (..., 3)."""
    x = np.clip(x, 0.0, 1.0)
    r = np.clip(3.0 * x, 0, 1)
    g = np.clip(3.0 * x - 1.0, 0, 1)
    b = np.clip(3.0 * x - 2.0, 0, 1)
    return (np.stack([r, g, b], axis=-1) * 255).astype(np.uint8)


def _chem(x: np.ndarray) -> np.ndarray:
    """Black -> teal -> white for x in [0, 1]."""
    x = np.clip(x, 0.0, 1.0)
    return (np.stack([0.6 * x ** 1.5, x, 0.5 * x + 0.5 * x ** 2], axis=-1) * 255).astype(np.uint8)


class AssocVideo:

    def __init__(self, seg, marks: dict[str, tuple[int, int, int]], cell_px: int = 22,
                 chem_px: int = 6, c_scale: float = 1.0):
        self.sx, self.sy, self.sz = (int(s) for s in seg)
        self.marks = marks
        self.cell = int(cell_px)
        self.chem_px = int(chem_px)
        self.c_scale = float(c_scale)
        self.frames: list[np.ndarray] = []

    def _grid_panel(self, a_g: np.ndarray) -> Image.Image:
        c, gap = self.cell, 8
        w = self.sz * (self.sx * c + gap) + gap
        h = self.sy * c + 2 * gap
        img = Image.new("RGB", (w, h), (12, 14, 23))
        d = ImageDraw.Draw(img)
        a = a_g.reshape(-1)
        cols = _heat(a)
        for g in range(len(a)):
            x, y, z = self._coords[g]
            x0 = gap + z * (self.sx * c + gap) + x * c
            y0 = gap + (self.sy - 1 - y) * c
            d.rectangle([x0, y0, x0 + c - 2, y0 + c - 2], fill=tuple(int(v) for v in cols[g]))
            if a[g] >= ACTIVE_THRESHOLD:
                d.rectangle([x0, y0, x0 + c - 2, y0 + c - 2], outline=(255, 255, 255), width=2)
        for name, (x, y, z) in self.marks.items():
            x0 = gap + z * (self.sx * c + gap) + x * c
            y0 = gap + (self.sy - 1 - y) * c
            d.rectangle([x0 - 2, y0 - 2, x0 + c, y0 + c], outline=MARK_COLORS.get(name, (200, 200, 200)), width=2)
            d.text((x0 + 3, y0 + 3), name, fill=(0, 0, 0))
        return img

    def _chem_panel(self, c_proj: np.ndarray, label: str) -> Image.Image:
        x = c_proj / max(self.c_scale, 1e-6)
        rgb = _chem(x)[:, ::-1].transpose(1, 0, 2)  # (y, x, 3), y up
        img = Image.fromarray(np.ascontiguousarray(rgb)).resize(
            (rgb.shape[1] * self.chem_px, rgb.shape[0] * self.chem_px), Image.NEAREST)
        d = ImageDraw.Draw(img)
        d.text((4, 4), f"{label} (max over z, scale {self.c_scale:g})", fill=(255, 255, 255))
        return img

    def set_group_coords(self, group_cell: np.ndarray):
        self._coords = [tuple(int(v) for v in row) for row in group_cell]

    def add(self, a_g: np.ndarray, c1: np.ndarray | None, c2: np.ndarray | None, header: str):
        panels = [self._grid_panel(a_g)]
        for c, lab in ((c1, "C1"), (c2, "C2")):
            if c is not None:
                panels.append(self._chem_panel(c.max(axis=2), lab))
        w = max(p.width for p in panels[:1]) + sum(p.width + 8 for p in panels[1:])
        h = max(p.height for p in panels) + 26
        frame = Image.new("RGB", (w + (w % 2), h + (h % 2)), (12, 14, 23))
        x = 0
        for p in panels:
            frame.paste(p, (x, 26))
            x += p.width + 8
        ImageDraw.Draw(frame).text((6, 6), header, fill=(230, 230, 230))
        self.frames.append(np.asarray(frame))

    def write(self, path: str, fps: int = 30) -> int:
        if not self.frames:
            return 0
        import imageio
        h = max(f.shape[0] for f in self.frames)
        w = max(f.shape[1] for f in self.frames)
        h += h % 16 and 16 - h % 16
        w += w % 16 and 16 - w % 16
        writer = imageio.get_writer(path, fps=fps, codec="libx264", quality=8, pixelformat="yuv420p")
        for f in self.frames:
            canvas = np.full((h, w, 3), 12, dtype=np.uint8)
            canvas[:f.shape[0], :f.shape[1]] = f
            writer.append_data(canvas)
        writer.close()
        return len(self.frames)
