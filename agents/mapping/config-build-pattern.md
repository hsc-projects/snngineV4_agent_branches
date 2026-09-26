# Config → template → build pattern

Reproduces the user's own description of the architecture (given in
dictation, not inferred beforehand) against the actual code, to confirm it
or surface contradictions. This is architecture-as-built, not a design the
user is committed to as "correct." See the note at the end.

## The user's description (paraphrased from dictation)

Pydantic config models are used as a template: an abstract, general
description of a network, that is then "built" into a corresponding
runtime object graph, which the UI then interacts with, and which is then
simulated. The abstraction holds at the top of this chain, but breaks down
(becomes particular/hand-written rather than general) near the edges,
specifically around leaf-level object construction (sub-visuals,
constructors). This wasn't a deliberate design tradeoff decided up front;
the difficulty of cleanly mapping Pydantic models onto arbitrary runtime
objects was underestimated when the rewrite (V2 to snngineV4) started.

## Confirmed: the abstract layer

`construction/engine_element.py` and `construction/nn_builder.py` are
genuinely generic, not neuron-specific:

- `EngineElementConfig` (Pydantic `ConfigModel` subclass,
  `construction/engine_element_config.py`) is the config/template side.
- `EngineElement` (`BuilderDict` subclass) is the built/runtime side. Which
  config class maps to which runtime class is driven by two class-level
  dicts, `BUILDER_OBJECT_CLASS_MAP` and `BUILDER_OBJECT_SUPERCLASS_MAP`
  (the latter pre-populated with generic conversions: typed-dataframe
  configs to `TensorDataFrame`, series configs to `TensorSeries`, etc.);
  this mapping mechanism has no knowledge of neurons, synapses, or any
  domain concept.
- Config fields are walked generically via a `node_tree`
  (`EngineNodes`/`ModelTree`). Typed dataframe/series fields are likewise
  auto-converted to tensor-backed runtime attributes by
  `EngineElement.set_tensor_attr`, generic machinery with no
  neuron-specific logic in it.
- `NetworkBuilder.build()` (`construction/nn_builder.py`) is the entry
  point: takes the template (`EngineConstructionConfig`, defined in
  `config/template.py`, currently just a thin wrapper holding one
  `network: SpatialNetworkConfig` field), deep-copies and re-dumps it, and
  drives the above generic machinery to populate itself (a `BuilderDict`)
  with `{config_model: built_object}` pairs.

This confirms the user's description: this part of the pattern really is
abstract/reusable, not particular to this project's domain.

## Confirmed: the particular edges

Two clear examples where the same pattern stops being generic, found by
tracing where construction reaches an external, fixed API this project
doesn't control:

1. **The CUDA/pybind11 boundary**: `nn/sim/simulation.py`'s
   `Simulation._make_simulator_backend` constructs `SnnSimulation` (the
   pybind11-wrapped C++ object) with ~30 individually named keyword
   arguments, each a raw `.data_ptr()` off a specific tensor (`N_pos`,
   `N_flags`, `N_states`, `G_stdp_config0/1`, `C_old`/`C_new`/`C_source`,
   etc.; see `agents/mapping/vertical-trace.md`'s case study for one of
   these, `N_pos`, in detail). Nothing about this is driven by the
   generic config-to-object map; it's a fixed, hand-written constructor
   call matching a fixed C++ signature. The abstraction can't extend past
   this point because the thing on the other side (compiled CUDA/pybind11
   code) isn't itself model-driven.

2. **The VisPy visual-construction boundary**:
   `visualization/visual_builder.py`'s `VisualMixins.mix` classmethod is
   an explicit `if`/`elif` chain, one branch per concrete VisPy visual
   class (`Line`/`XYZAxis` vs. `Box`/`FiniteGridLinesVisual` vs.
   `MeshVisual` vs. `Markers`/`CompoundMarkersVisual` vs. the `Volume`
   family), each requiring hand-specified `attr_changed_keys`, and it
   raises `NotImplementedError` for any visual class not explicitly
   enumerated there. Adding a new leaf visual type means adding a new
   branch by hand; there's no generic rule that covers "any VisPy visual."
   Same underlying cause as (1): VisPy's own visual constructors aren't
   uniform, so nothing generic can paper over that at the last step.

3. **The base-template to visual-config field-ownership boundary**: this
   third edge was found by tracing a conflict the user described from
   memory and confirming it in code, the reverse order from the other
   two, which were found by tracing construction first. A visual config
   (e.g.
   `MarkersVisualConfig`) often needs a field that the base/simulation
   template already owns (e.g. `pos`); mapping both into the UI would
   either duplicate the same property twice, or leave it ambiguous which
   one is authoritative. The resolution is a deliberate, named three-way
   policy, repeated by hand in every visual config file that needs it
   (`markers.py`, `boxes.py`, `lines.py`, `mesh.py`), each explicitly
   labeled `# --- Ownership policy (Phase 3) ---` (implying earlier,
   presumably less settled phases preceded it):
   - *Source-canonical* (read-only proxy, must not write here): e.g.
     `pos_origin`, owned by `NetworkReservoirConfig`; the visual config
     just reflects it.
   - *Shared-runtime resource* (in-place mutation only, no reassignment):
     `pos` specifically. Not two values to reconcile; the visual's
     `pos` and the base template's `pos` are the same underlying array
     object. Marked via a `SHARED_RUNTIME_FIELDS: ClassVar[frozenset[str]]`
     class attribute, and enforced at runtime in
     `gui/parameter_trees/connectors/object2object_links.py`
     (`prepare_object`'s `set_attr`): reassigning a shared field to a
     different array raises `RuntimeError`, forcing in-place mutation
     (`arr[:] = ...`) instead.
   - *Visual-canonical* (locally owned, writable via param tree): e.g.
     `size`, `edge_width`, `edge_color`, `face_color`. These are genuinely
     visual-only, so no duplication concern applies.

   So this conflict is resolved, correctly and deliberately, but by
   hand, per field, per visual config class, via a repeated code comment
   plus a manually-maintained `frozenset`. A new shared field means
   someone deciding by hand which of the three categories it falls into
   and writing it down again; there's no rule that classifies a field
   automatically. Same shape as edges (1) and (2): a real, working
   solution, just not a generalized one.

Three edges, found by two different routes (tracing construction code
outward, and confirming a remembered conflict in code), landing on the
same underlying shape each time: this project's own generic config/build
machinery works cleanly until it meets something with its own fixed,
non-uniform requirements, whether that's a compiled extension's
constructor, an external library's non-uniform visual classes, or a UI's
need to show one property once despite two config models both claiming
it. At that point the abstraction stops and hand-written, per-case
resolution takes over.

## Note on how to treat this

Per the user directly: despite the rough edges above, this pattern should
still be treated as *the* architecture for now. It covers the important
parts, and at this point, with the project not being extended heavily
anymore, reworking it isn't worth doing. This is not the same as it being
endorsed as the ideal or a considered best practice: the user explicitly
did not follow an established design pattern here, arrived at it through
building what they wanted rather than research, and is open to a better
pattern existing for this same problem (config-driven object
construction feeding into a rendering/simulation loop is a problem every
3D engine or game engine has to solve somehow). See
`agents/research-todos.md` for the comparison-to-established-patterns
question this raises, which is a separate, later task, not a reason to
second-guess or rework this pattern now.
