# Task: local GPU/CUDA-OpenGL-interop smoke test

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

**Phase 1 (do this first):** adapt the existing PyQt+VisPy app into a
minimal script that still exercises the real interop chain and actually
renders something on screen, using the real project code (not a
from-scratch reimplementation). This is a visual check — no automated
pass/fail needed, the maintainer will run it and confirm by eye.

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

- `interop_smoke_test_incl_gui.py` — phase 1's minimal visual script.
- `gpu-smoke-test-report.md` — a proper report per phase, per "Reporting format" below,
  plus any config-change proposal from "Working autonomously" above.
- `auto.py` — phase 2's automated, headless check.

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
