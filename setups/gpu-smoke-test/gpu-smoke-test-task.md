# Task: local GPU/CUDA-OpenGL-interop smoke test

## Safety: never launch this script's GUI window yourself (verified 2026-09-28)

**Confirmed via `journalctl`, not just a timing coincidence:** at
14:14:22 on 2026-09-28, `gnome-shell` actually crashed (SIGABRT), 13
seconds after this script's window would have been created (its bytecode
cache was written at 14:14:09):

```
meta_window_set_stack_position_no_sync: assertion 'window->stack_position >= 0' failed
libmutter:ERROR:../src/core/window.c:5532:meta_window_get_workspaces: code should not be reached
GNOME Shell crashed with signal 6
```

with the crashing stack trace inside the **`tiling-assistant@ubuntu.com`**
GNOME Shell extension (`tilingWindowManager.js`/`moveHandler.js`). **This
is not a CUDA/GPU driver crash** — an earlier version of this note guessed
that mechanism and was wrong. The real bug is a Mutter assertion failure
in the tiling-assistant extension's window move/stacking handler, which
aborts the whole `gnome-shell` process — and with it, the entire desktop
session — regardless of whether the app that triggered it is doing
anything wrong. Separately, running the script directly (in PyCharm, same
day) produced only an ordinary Python exception (see the engine bug below)
with no crash, consistent with this being a timing/window-state-sensitive
WM bug rather than something the script deterministically triggers on
every run.

**Rule: you (the agent) must never call this script's GUI path
(`main()` / `MinimalEngineApp()` / `app.run()`) yourself**, on this
display or any other live session — a newly created/shown window can
crash the maintainer's whole GNOME session through this extension bug,
independent of whether the script's own code is correct. Write and edit
the script freely; static checks (`python -m py_compile`, or importing
the module without calling `main()`) don't create a window and are safe
to run yourself. Actually launching it to see it render is the
maintainer's step alone (or done with the maintainer watching/driving) —
not something to work around by inventing a nested/virtual display
without proposing that first, per this repo's rule against unprompted
workaround scripts.

**Bug found in the earlier import-based attempt, blocking its visual
check:** `numba_device_array` in
`snngine_v4/visualization/cuda/gl_interop/gl_buffer.py` (around line 98)
constructs a `numba.cuda.cudadrv.devicearray.DeviceNDArray` that numba's
`require_device_memory` rejects with `Exception: Not a CUDA memory
object.` That's the whole finding — root cause not investigated further
(don't guess at the mechanism without reading `gl_buffer.py` and numba's
`DeviceNDArray`/`require_device_memory` yourself first). This is in the
engine's own code (`snngine_v4/visualization/...`), out of this task's
scope to fix (see "Scope" above) — flag it for whoever owns that module
rather than patching it here.

**Scope: this host only.** Do not touch RunPod, credentials, or any cloud
resource. Once this works here, running it on a RunPod pod is a separate
follow-up task, not part of this one.

**File/command boundary:** stay confined to this project
(`snngineV4_agent_branches/`) and its sister repo
(`SNNgine3D_agent_branches/`, read-only reference — see "Fallback" below)
for everything in this task, including the config changes and helper
scripts mentioned further down. Don't read, write, or run anything outside
these two directories.

**Working directory:** all paths below are given relative to
`snngineV4_agent_branches/` unless stated otherwise — if your actual
starting directory is its parent (`snngineV4_cloud/`, containing both
`snngineV4_agent_branches/` and `SNNgine3D_agent_branches/` as siblings),
prefix each path below with `snngineV4_agent_branches/` accordingly.

## Working autonomously

Proactively look for anything in this project's own config (permissions,
tool-approval settings, environment variables, or similar) that would let
you work end-to-end with less manual confirmation, not just when already
blocked by it. Propose the exact change and why it's needed in `gpu-smoke-test-report.md`
(in this same directory) as soon as you identify it, then keep working on
whatever doesn't depend on it while that's pending.

## Helper scripts are fine

Write helper scripts freely wherever they reduce the number of manual
commands or repeated steps needed (e.g. an env-activation wrapper, a
rebuild/rerun loop) — explicitly allowed for this task, not something to
ask about first.

Same for Dockerfiles/images: create and freely modify your own for this
task (e.g. for the future container/pod work below) — the existing
`setups/Dockerfile-SNNgine3D-nomachine(-base)` files aren't running
anywhere, so they're fair game too if reusing/editing them helps. Don't
touch any *other* compose file, container, or image on this host — this
task's containers are the only ones in scope; other projects (e.g. this
machine's separate sandbox-container setup) are not.

## Goal — two phases, work through both autonomously

The full interop chain already works on this host: `main` runs without
issues under the `snngine` conda env (confirmed by the maintainer) — this
task isn't re-establishing that. The goal is a much lighter, re-runnable
way to check it.

**Redirect (2026-09-28): Phase 1 must be self-contained, not built on the
engine's config/network/GUI machinery.** The first version of this script
imported the real `snngine_v4` classes (`EngineConfig`, `SNNgine`,
`EngineParameterTree`, `GLBufferMap`, ...) to build a full window through
the actual engine machinery. That's the wrong shape for a lightweight
smoke test — it pulls in the entire config/network/parameter-tree stack
just to exercise a 5-step interop chain, and it means a bug anywhere in
that stack (as happened: `gl_buffer.py`'s `numba_device_array`, see below)
blocks the smoke test even though the interop mechanism itself might be
fine. Rewrite Phase 1 as a **minimal script that avoids that stack**,
following the chain's shape from `agents/mapping/vertical-trace.md` (the
same 5 links as "The interop chain to exercise" below): a small CUDA step,
a small VisPy-rendered GPU buffer, that buffer registered/mapped for
CUDA↔OpenGL interop, wrapped as a `numba.cuda` device array, then
`torch.as_tensor(...)` over that.

**Imports are fine where unavoidable — this is about avoiding the engine's
config/GUI/network stack, not about avoiding imports as such.** In
particular, don't feel obligated to hand-write and compile a new CUDA
kernel from scratch today: `SNNgine3D_agent_branches/notebooks/
simulation_demo/sim_demo_utils.py` (sister repo, read-only reference —
see "Fallback" below) already has a small, working, hand-written kernel
(`update_N_state`, compiled via `pycuda.compiler.SourceModule`) with no
config/network/GUI dependency at all, plus a `TorchHolder
(cuda.PointerHolderBase)` class showing how that kernel writes directly
into a CUDA `torch.Tensor`'s memory. Reuse or import that instead of
writing new CUDA code — it's real, already-working code, not a suggestion
to verify from scratch. Note it doesn't cover the VisPy/GL side of the
chain (no GL buffer there, just PyCUDA↔Torch), so link 3 (PyCUDA↔VisPy GL
buffer) still needs its own, separately-verified piece. The exact API
calls (PyCUDA's
specific GL-interop entry points, how the buffer is created/registered,
etc.) are not prescribed here and haven't been verified against current
library versions — look them up (PyCUDA/numba/VisPy's own docs or source,
or this project's own working usage of them) rather than assuming any
particular call signature is correct. This is about proving the mechanism
works standalone, not about exercising this project's actual
network/visual-config code. A few dozen neurons/vertices is plenty;
there's no need to reproduce real simulation behavior, config trees, or
the parameter-tree GUI at all.

**Make the CUDA-kernel step optional so the rest of the chain can still be
checked if it doesn't work.** Don't let a failure in the compiled/
hand-written CUDA kernel step (link 1) abort the whole script: wrap that
step so that if it fails (or is skipped outright), the script falls back
to driving the per-frame buffer mutation some other way instead — e.g.
writing directly through the `torch.Tensor`/`numba.cuda` device-array
view with ordinary tensor/array operations, no custom kernel involved —
and continues through buffer registration, the `numba.cuda` wrap,
`torch.as_tensor(...)`, and the live write-through check below. The goal
is to get a confirmation that links 2–5 (the actual interop mechanism this
smoke test exists to check) work even on a run where link 1 doesn't.
Report which path actually ran (kernel vs. fallback) in
`gpu-smoke-test-report.md`.

**Must prove a live write-through, not just that the chain constructs.**
Successfully building the `torch.as_tensor(...)` view over the mapped
buffer isn't the check — writing through it and seeing VisPy's on-screen
visual actually change as a result is. Drive a small per-frame update
(a VisPy timer or the app's own event loop) that repeatedly mutates the
GPU buffer via the `torch.Tensor` view (e.g. nudge vertex positions, or a
color channel if the chosen visual exposes one at a known offset — decide
the actual buffer layout for whatever minimal VisPy visual you pick,
don't assume it matches `vertical-trace.md`'s `N_pos`/`MarkersVisual`
case study, which is specific to that buffer and that visual class) with
no explicit copy back to VisPy — the visual updates only because the two
are the same underlying memory. That's the actual zero-copy claim this
smoke test exists to check; a static single-frame render would not
exercise it.

**Phase 1:** this self-contained script still exercises the real interop
chain and actually renders something on screen. This is a visual check —
no automated pass/fail needed, the maintainer will run it and confirm by
eye (see "Safety" above: the agent writes and statically checks this
script but does not launch its GUI path itself).

**Phase 2 (continue immediately after, no need to wait for check-in):**
build a separate, lightweight *automated* check (asserts on the actual
buffer/tensor wiring: PyCUDA↔OpenGL buffer, `numba.cuda` device array,
`torch.as_tensor` view) that can run unattended, without a display.

When phase 1 is done, append a proper report for it to `gpu-smoke-test-report.md` (in this
same directory) before continuing to phase 2 — don't wait for a response,
just keep going. Do the same for phase 2 when it's done. See "Reporting
format" below for the structure each phase's report should follow.

## The interop chain to exercise

Read `agents/common.md`'s "Core technical facts" section first (see
`agents/glossary.md` for precise definitions of "CUDA/OpenGL
interoperability" and "zero-copy"):
1. Hand-written CUDA simulation code.
2. PyCUDA built with OpenGL interoperability.
3. PyCUDA buffers compatible with VisPy's OpenGL buffers — confirmed in
   `snngine_v4/visualization/cuda/gl_interop/gl_buffer.py`.
4. That mapped memory wrapped as a `numba.cuda` device array — same file.
5. PyTorch wrapping that device array via `torch.as_tensor(...)` —
   confirmed in `gl_tensor.py`.

Exception noted in `common.md`: 3D textures (`gl_texture3d.py`) don't get
true zero-copy — they fall back to an explicit `pycuda.driver.Memcpy3D`
GPU-to-GPU copy. Worth knowing, not this smoke test's main target (the
VBO/IBO path 1–5 above is).

## Environment

- Conda env `snngine` already exists and works: `conda activate snngine`,
  or directly `/home/htm/anaconda3/envs/snngine/bin/python`.
- This host: Ubuntu 24, RTX 3090, driver `595.91.07`, compute capability
  `8.6`. System `nvcc` reports toolkit `12.0`, separate from whatever
  `torch==2.8.0` (`cu129`) bundles — relevant since `pycuda` compiles
  kernels at runtime against the system toolkit. Note any mismatch found
  here rather than assuming it's fine.
- A real display session is active (`DISPLAY=:1`) — phase 1 can open an
  actual window.

## Prior attempt (reference only, don't restart from here)

`setups/Dockerfile-SNNgine3D-nomachine(-base)`: a Docker-based attempt using
`nvidia/cudagl:11.4.2-devel-ubuntu20.04`, a full `xfce4` desktop session
inside the container, and NoMachine (`nxserver`) as the remote-desktop
transport into it; PyCUDA was built from source (`v2022.2`,
`--cuda-enable-gl`). Remote-desktop connectivity itself was confirmed
working previously; getting the actual GPU rendering to work under it was
not (why this Docker work was dropped from version control in the
SNNgine3D sister repo). No project-specific smoke-test script exists in
the Dockerfile — only PyCUDA's own generic bundled test directory was
copied in, whose outcome is unknown. This is about a future container/pod
step (see below), not this task's host-only scope.

## Fallback if the full chain proves too hard to wire up directly

The sister repo's `notebooks/` directory has simulation-only-focused code
(no PyQt UI, narrower scope) usable as a simpler basis if needed:
`SNNgine3D_agent_branches/notebooks/` (sibling of `snngineV4_agent_branches/`
under the shared parent directory — see "Working directory" above).

## Deliverables (all in this same `gpu-smoke-test/` directory)

- `interop_smoke_test_standalone_gui.py` — phase 1's minimal script that
  avoids the engine's config/network/GUI stack (see "Redirect" above;
  importing a small existing piece, e.g. a kernel, is fine). Same naming
  pattern as the file below; any other new file this task adds follows the
  same `interop_smoke_test_<descriptor>.py` pattern.
- `gpu-smoke-test-report.md` — a proper report per phase, per "Reporting format" below,
  including a focused Python snippet illustrating the `gl_buffer.py` failure from the
  initial monolithic attempt, plus any config-change proposal from "Working autonomously" above.
- `interop_smoke_test_auto.py` — phase 2's automated, headless check (same
  naming pattern; avoids the engine's config/network/GUI stack for the
  same reason as phase 1, same allowance for unavoidable imports).

Don't edit `runpod-rationale.md` — closing that open item is a separate
later step that will use this task's findings.

## Reporting format

Each phase's entry in `gpu-smoke-test-report.md` follows `setups/report-format.md`'s
shared convention (summary at top, details in subsections below) — read
that file for the exact structure.

## Future: adapting this for a container/pod (not in scope now)

Once both phases work on the host, making the visual check work inside a
Docker container is a separate future task (relevant for the eventual
RunPod pod image). Options identified, ranked:

1. **EGL headless rendering (top pick).** NVIDIA's driver supports an
   OpenGL context via EGL with no X server, virtual display, or
   remote-desktop protocol at all — the standard path for GPU-accelerated
   OpenGL in headless containers (`nvidia-container-toolkit`'s own
   examples use it). If VisPy's backend can target an EGL surface instead
   of a window, this renders straight to a framebuffer and saves an
   image — avoids the whole desktop/remote-desktop layer the prior
   NoMachine attempt struggled with. Open Khronos standard; the actual
   implementation is this host's already-installed, already-licensed
   NVIDIA driver.
2. **VirtualGL + TurboVNC.** Both open source and free for commercial use
   (wxWindows/LGPLv2.1-style, and an X.org-based fork respectively) —
   purpose-built specifically for streaming GPU-accelerated OpenGL out of
   a container, a better-targeted tool for this than NoMachine's general
   remote-desktop scope. Worth trying if an interactive/live view is
   wanted, not just a still image.
3. **NoMachine (lowest priority, reference only).** See "Prior attempt"
   above — don't restart from here unless 1 and 2 both fail.

This section is a forward-looking note, not something for this task to
act on now.
