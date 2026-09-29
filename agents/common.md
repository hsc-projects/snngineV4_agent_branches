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

The CUDA simulation code is based on Nageswaran et al., "Efficient
simulation of large-scale spiking Neural networks using cuda Graphics
processors" (referenced in snngineV4's `nn/NDKNV/`; full entry in
`agents/references.md`) — the basic/foundational algorithm. It was
implemented first as a direct translation of that paper, then
progressively optimized (simplifications, matrix-operation tricks) to
accelerate it further. Understanding kernel-level detail is deferred (see
Workflow) until the user provides source material on the algorithm and its
optimizations.

See `agents/glossary.md` for term definitions (e.g. what "CUDA/OpenGL
interoperability" and "zero-copy" mean precisely).

The network is a fixed-size block of neurons in 3D space, called a
"reservoir" in the codebase (`NetworkReservoir`; see the glossary for why
this term may not strictly apply here).

Synapse count per neuron is fixed to avoid warp divergence (see glossary):
the synapse array has shape N × S, where N is the neuron count and S is
the fixed synapse count per neuron.

Connection probability is computed in CUDA construction code
(`snn_representation.cu`, function `sigmoidal_connection_probability`) as
a function of the discretized group-to-group delay, separately for
inhibitory and excitatory connections. Probability decreases with delay,
so nearby groups are favored over distant ones.

Generating this connectivity on every network build is currently
considered closed, but has been a source of past bugs and may require
revisiting.

During network construction, the connectivity search is delay-dependent
and uses randomness to find a valid neuron to connect to. This causes
strong warp divergence in practice: many threads finish early and sit
idle while others keep searching for their next valid connection.

## Workflow

Do not commit or push without explicit approval from the user.

If the user asks a question, answer it. Full stop. Do not interpret a
question as a prompt to take actions, execute commands, or modify files.
Answer the question directly and wait.

When the user dictates an explanation that needs organizing, clean it up
into sensible prose — that's expected. Don't invent claims, comparisons,
or framing that weren't actually said. Before turning it into prose,
identify any vague or underspecified parts and ask about them first, as
questions — don't fill the gap yourself and ask "is this OK?" afterward.

Never write an edit based on inferred or implicit confirmation (the
conversation moving on, an unrelated reply, silence). Only an explicit yes
tied to that specific content authorizes writing it.

Preserve the user's stated confidence level when writing something down.
"Cleaning up" dictation means making it more precise and factual, not more
polished-sounding — if they say "I think," "maybe," "probably," or express
uncertainty, keep that uncertainty visible in the written text (e.g.
"unconfirmed," "the user believes," "not verified against the code")
rather than flattening it into a confident declarative statement for the
sake of smoother prose. When the uncertainty is about something checkable,
proactively offer to verify it (read the code, do a web search) rather
than just recording the hedge and moving on.

This isn't limited to uncertainty the user flags with a hedge. When *you*
are about to state or act on something you're not confident about, be it
how a piece of code behaves, an equation, or a claimed fact, verify it
against the primary source (the actual code, the paper) first, rather
than generalizing from a plausible-sounding guess. Guessing here has caused
real problems before.

When the user gives several sentences elaborating, hedging, or giving
examples around a point, treat that as raw material to help formulate one
concise, accurate statement, not as dictation to transcribe verbatim or
preserve sentence-by-sentence. Distill to the essential point. This
doesn't override the confidence-level rule above: real uncertainty about a
fact still stays visible in the final text, but throwaway hedges from the
process of recalling/describing something don't each need their own
clause.

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

During code mapping (vertical and horizontal passes), don't dig into CUDA
kernel implementation details. Treat the CUDA/kernel layer as accelerated
compute understood by its *intent*, as inferred from the surrounding
Python code — not by reading kernel internals. Deep understanding of the
simulation algorithm itself is deferred until the user provides the
underlying source material (see `agents/references.md`). Avoid cluttering
context with kernel-level detail not needed for the current pass.

When documenting code in `agents/mapping/`, favor tagging over restating
what's easily inferable from the code itself (avoid re-describing what a
directory listing or grep would already show). Propose new tags to the
user before introducing them, and check `agents/tags.md` first — reuse an
existing tag if one fits rather than creating a near-duplicate.

Features/work items and to-dos are tracked in `agents/feature-todos.md`
(Now / Backlog / Paused / Questions, each entry tagged with a priority —
high, mid, or low). Confirm entries with the user before adding/moving them.

If you notice yourself blending two distinct tasks the
user gave separately (doing both, merging their outputs, or deciding on
your own where a later one's output should live relative to an earlier
one's), stop and ask, rather than deciding it yourself, even if the tasks
came up in the same conversation about the same topic. Being asked to do
one is not permission to also do the other, or to decide how they
relate. This has actually gone wrong before: documenting what this
project's own code/architecture currently does, and researching how that
compares to other existing software/patterns, got folded into the same
write-up on the writer's own judgment instead of being kept as separate
asked-for tasks.

Most of the code/ideas here are not sourced from external research — this
project grew out of self-taught exploration of a visual idea, not scientific
grounding. If something in the code looks like it corresponds to existing
research, an established algorithm, or a concept that should be
sourced/verified, flag it to the user rather than assuming — don't research
it inline, just add it to `agents/research-todos.md`.
