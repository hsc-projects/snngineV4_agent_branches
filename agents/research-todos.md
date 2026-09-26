# Research to-dos

Items flagged during exploration that look like they might correspond to
existing research, an established algorithm, or a concept that should be
sourced/verified — to confirm with the user later. Most of this codebase was
built without scientific grounding (see AGENTS.md → History), so anything
suspicious should land here rather than being assumed correct.

- Nageswaran, Dutt, Krichmar, Nicolau, Veidenbaum. "A configurable
  simulation environment for the efficient simulation of large-scale
  spiking neural networks on graphics processors." *Neural Networks*,
  2009. ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0893608009001373))
  Likely the extended journal version of the Nageswaran et al. IJCNN 2009
  paper already in `agents/references.md`, by the same authors. Confirmed
  by the user to be in their personal library, but not confirmed as
  actually used/read for this project. Worth reviewing later for anything
  applicable.

- Compare snngineV4's config→template→build pattern (see
  `agents/mapping/config-build-pattern.md`) against established patterns
  used by other 3D/game engines for the same problem: config-driven
  object construction feeding a rendering/simulation loop. The user
  arrived at this pattern by building what they wanted, not by following
  an existing recipe, and is open to there being a better-known pattern
  for it, without intending to rework the current one now. This is not
  urgent; it is a later comparative-research task, not a prompt to
  reconsider the current architecture.
