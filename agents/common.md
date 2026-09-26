# Common

Shared content for agents working in either SNNgine3D or snngineV4. Both
repos' `AGENTS.md` point here — edit this file, not the pointers.

## Goal

Overarching goal: simulate and visualize spatially extended Spiking Neural
Networks, in service of a broader idea the user has in mind and will expand
on later. "Spatially extended" matters: the 3D placement of neurons in the
room is meaningful to the idea, not incidental — placement is not expected
to stay random.
*[placeholder — to be filled in]*

The goal is to realize this idea as fast as possible — this is where agents
(like you) come in: the mapping/documentation work is meant to let cold
agents get productive quickly and drive the project forward.

## Core technical facts

The core of both SNNgine3D and snngineV4 is the same hand-written CUDA code,
ported from V2, mostly dedicated to simulating spiking neural networks. This
is probably the most important core technical fact about the project.

Five pieces make up the technical chain:

1. The self-written CUDA simulation code itself, ported from V2.
2. PyCUDA built with OpenGL interoperability activated.
3. PyCUDA buffers defined to be directly compatible with VisPy's OpenGL
   buffers.
4. That PyCUDA-mapped memory is wrapped as a `numba.cuda` device array —
   numba is the bridge that makes it usable by PyTorch.
5. PyTorch wraps the numba device array via `torch.as_tensor(...)`, giving
   a PyTorch tensor backed by the same GPU memory (confirmed in
   `snngine_v4/visualization/cuda/gl_interop/gl_buffer.py` and
   `gl_tensor.py`).

Pointers to the buffers from (2)–(5) are passed into the CUDA code from (1).
Order: when visualization is involved (very probably always the case),
VisPy generates the OpenGL buffer first, producing an OpenGL buffer ID. A
PyCUDA buffer is then defined around that existing OpenGL ID (confirmed:
`pycuda.gl.RegisteredBuffer(opengl_id)` in `gl_buffer.py`), giving CUDA and
VisPy shared access to the same GPU memory.

Exception: 3D textures. Volumetric visuals (used to visualize chemical
concentration in the room, i.e. `chemistry/` volumes) do not achieve the
same zero-copy interoperability as the VBO/IBO path above. Getting true
zero-copy OpenGL interop working for 3D textures proved very difficult and
was not solved — the current solution falls back to an explicit GPU-to-GPU
copy (`pycuda.driver.Memcpy3D`, confirmed in `gl_texture3d.py`) between a
separately-allocated PyTorch tensor and the OpenGL texture, each time data
needs to move between them.

## Workflow

Do not commit or push without explicit approval from the user.

Any markdown files you create (notes, extracted write-ups, etc.) land under
`agents/` in snngineV4 (the new repo).

We are in an exploratory/mapping phase: the goal is not to generate new code
(except where it aids exploration) — make the content as easy as possible for
cold agents to understand.

Explain findings rather than assuming shared context, and give the user room
to confirm or correct your understanding as you go, rather than presenting
conclusions as settled.

Do not attempt to lint, test, or run the main script/application, regardless
of phase (mapping/planning/building). This code needs a PyQt UI, an NVIDIA
GPU for simulation/visualization, and PyCUDA built with OpenGL interop
enabled — which almost certainly requires a local build not available in
this environment.

Documentation is sparse/missing in places. When intent is unclear, ask the
user — but do not expect real technical documentation to be provided; infer
from code where possible.

Features/work items and to-dos are tracked in `agents/feature-todos.md`
(Now / Backlog / Paused / Questions, each entry tagged with a priority —
high, mid, or low). Confirm entries with the user before adding/moving them.

Most of the code/ideas here are not sourced from external research — this
project grew out of self-taught exploration of a visual idea, not scientific
grounding. If something in the code looks like it corresponds to existing
research, an established algorithm, or a concept that should be
sourced/verified, flag it to the user rather than assuming — don't research
it inline, just add it to `agents/research-todos.md`.
