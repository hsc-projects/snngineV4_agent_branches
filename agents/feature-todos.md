# Feature to-dos

Tracks features/work items across SNNgine3D and snngineV4. Confirm entries
with the user before adding/moving them (same as any other fact in this
`agents/` directory) — see `agents/common.md` → Workflow.

Each entry gets a priority: **high**, **mid**, or **low**.

## Now

- [high] Fetch and read the three reference papers (`agents/references.md`)
  into context, not equally weighted:
  1. Nageswaran et al., 2009 (highest value). The codebase's CUDA
     implementation is a variant of this paper: same algorithmic base,
     with some self-written kernels later replaced by standard CUDA
     matrix operations. Read this first and in full. The paper also
     establishes the vocabulary/terminology used for this domain, useful
     beyond just understanding the code itself. Public code from the same
     research group exists as CARLsim
     (github.com/UCI-CARL/CARLsim6), useful to cross-check or confirm
     details if the paper alone is unclear.
  2. Izhikevich, 2003 (secondary). Needed mainly for the neuron model's
     equation and parameters, largely to confirm those are being
     interpreted correctly; that content likely already appears within
     paper 1 too. Lower priority than paper 1; could also just be checked
     against a web source rather than fully read.
  3. The "shared memory" paper (currently the provisional Fidjeland &
     Shanahan match, unconfirmed). Lowest priority. Purpose in this
     codebase is not remembered: possibly STDP, possibly the simulation
     loop, possibly the chemical diffusion computation. Good to have in
     mind, not confirmed relevant to a specific subsystem.

## Backlog

- [mid] Implement an additional, less compute-intensive spiking neuron model
  — Integrate-and-Fire (IF) or Leaky Integrate-and-Fire (LIF) — alongside
  the existing Izhikevich model.
- [low] Revisit the 3D volumetric texture copy path (currently explicit
  `pycuda.driver.Memcpy3D` GPU-to-GPU copy, see `agents/common.md` → Core
  technical facts) — try again to achieve true zero-copy OpenGL interop for
  3D textures.
- [low] Restart a pure C++ version of the engine (a "sister" project to
  snngineV4, in the spirit of V2) developed in parallel and kept in sync
  with the Python version. If pursued, this would be managed by agents.
- [mid] Investigate slow application startup — specifically, importing the
  libraries (PyQt, Pydantic, etc.) at launch appears slow, before any
  network/simulation is loaded. Suspected culprits: PyQt itself, or the
  large number of Pydantic config models — unconfirmed which. Suspicion
  leans toward PyQt because the same slow-import pattern was observed in a
  separate, unrelated app that used no GPU/CUDA at all. Part of the
  motivation for the low-priority C++ sister-project idea above.
- [low] Survey related existing SNN simulation frameworks — BindsNET,
  Brian2 (and its GPU backends Brian2CUDA/Brian2GeNN), NeuroML — for
  relevant ideas or possible future interop. Not a core design driver, just
  worth being aware of what exists in this space.

## Paused

- [mid] Migrating the "simulation stepping" feature from SNNgine3D — see
  `agents/paused-migration-feature-simulation-stepping.md`.

## Questions

(nothing yet)
