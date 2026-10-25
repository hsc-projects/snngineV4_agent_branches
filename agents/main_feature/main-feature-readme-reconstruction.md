# Main feature: reconstruction of the lost README

> [!NOTE]
> **Status: inferred, not authoritative.** The original concise README of the
> main feature is missing; only its eight figures survive in
> `archive/docs_src_dump/readme_images/` (non-VCS, referenced by path only).
> This file reconstructs what the README most likely said, **using only what
> those figures show**, except the section "Minimal version", which comes from
> the user's later explanation. Per the user, parts of the original material
> may be wrong or outdated. Anything that is the reconstructor's reading, not
> the figures or a statement of the user, is marked *(inferred)*; at present
> none remain. Points the figures do not settle are listed under "Open
> points" at the end.
>
> **Two layers.** The *minimal version* (first section) is the one the user
> wants to implement first. The sections after "Definitions" describe the
> *full system*: autonomous and "biologically or physically plausible
> enough". The user believes the figure with the electrodes
> (`short_circuit_current.png`) is probably relevant to the minimal version
> only, so it appears there.

## Minimal version

The minimal version is the simplest implementation that still contains the
core idea; it is the one to implement first. Source: the user's explanation,
not the figures. Terms are defined under "Definitions" below.

**Goal.** Two concept assemblies, A and B, in R are activated together by
current injection. Tuned chemical releases and the corresponding STDP then
lead to the short circuit state. Afterwards R holds an associative memory:
activating one assembly activates the other. One direction (A to B, or B to
A) already counts as success.

**Core idea.** A and B have no knowledge of each other's positions in 3D
space, just as ordinary neurons have none. The association forms through the
spatial distribution of the chemicals released by activity alone.

**Main inspiration (stated by the user).** The core idea, or natural
phenomenon, behind [ant colony optimization
algorithms](https://en.wikipedia.org/wiki/Ant_colony_optimization_algorithms),
not the algorithm itself: there it plays out in practically 2D space, here in
3D. Spikes and weights plus pheromone-like chemicals take the place of ants
and pheromones.

**Main criterion (stated by the user).** It has to work *without cheating*,
i.e. stay physically and biologically plausible enough. In a big reservoir
the mechanism should work between any chosen pair of assemblies, not only for
a pair whose placement was tuned beforehand.

**Assembly in the minimal version** *(the user's suggestion: "could simply
be")*. An assembly is the set of neurons at one grid location (a location
group). The assembly counts as active when the average activity at that
location is above a certain level. The definition may still need refining.

**Allowed shortcuts.**
1. Increase the weights between the neurons within one location, so that
   activating a few of them activates the whole assembly. The user does not
   count this as cheating. It is also what makes current injection into a few
   neurons enough.
2. Neurons use up local energy (a mechanism that "could be allowed"). A short
   circuit can then concentrate activity around the relevant neurons and
   passively suppress the activity around others, without relying on
   inhibitory synapses. Its purpose is to facilitate the hardening under C₂.

**Current injection.**

![short circuit current](../../archive/docs_src_dump/readme_images/short_circuit_current.png)

The figure *(probably minimal-version only, per the user)* shows four steps in
R: (1) two assemblies A and B with neurons between them; (2) both assemblies
are activated by current injection through electrodes; (3) neurons between
them start to fire; (4) after the weights of the relevant synapses have been
modified with V-STDP, the pair is activated in a self-sustained but
time-limited way, through the "short circuit current".

**Fixed assumptions (stated by the user).**
- Chemicals are released in proportion to neuron activity, at the location of
  each neuron.
- STDP only reweights existing synapses; no synapses are created. (The
  synapse count per neuron is fixed in the engine.)

**Protocol** *(derived by the reconstructor from the concept; the user
confirmed it as intended)*:
1. **Joint activation rounds.** Inject current into A and B together, in
   place of the STMM-driven recall state. Active neurons release C₁ around
   themselves, and the STDP changes are non-permanent. Repeat until the test
   (step 3) succeeds; fewer rounds is better (stated by the user). The rounds
   let C₁ build up where activity repeatedly flows between A and B and not
   around neurons that fired only incidentally.
2. **Short circuit stage.** Keep A and B jointly active. C₂ is released in
   proportion to activity, and the weight changes become permanent where C₁
   and C₂ are both high.
3. **Test.** Inject current into A alone and check whether B becomes active
   (or the reverse).

**Left out of the minimal version:** PL, STMM, the VN and its glands, and the
dream state (in the full system, the autonomous trigger for the recall state).

**Overcoming distance is the point (stated by the user).** A and B may be
far apart and are not (or only weakly) directly connected. The minimal
version has to connect them anyway. Since no synapses are created, the
association has to form along multi-hop paths through existing synapses and
the neurons between A and B (confirmed by the user), which the spatial spread
of the chemicals selects. This requires that such a path exists, which depends on
the distance-dependent connection probability, the synapse count per neuron
and the delays; whether it exists in a given reservoir is part of what the
experiment shows.

## Definitions

- **seSNN**: the whole network, a spatially extended spiking neural network,
  i.e. one whose neurons have positions in space (the label of the dashed
  frame in the figures; expansion as in `agents/common.md`, Goal).
- **R (reservoir)**: a 3D block of neurons. Some of its neurons form
  *concept assemblies*; the rest are scattered between them.
- **Concept assembly**: a group of neurons in R that stands for one concept
  (drawn as a circled cluster, labelled A, B, … in later figures).
- **PL (projection layer)**: a 2D grid of neurons that sits between the
  other modules and projects activity into R.
- **STMM (short-term memory module)**: a separate module holding a group of
  neurons (drawn as a cube) that is connected to the PL.
- **VN (vascular network)**: a network of vessels with a *source* and a
  *sink* that carries chemical particles through R.
- **Chemical gland**: releases chemical particles into the VN (drawn inside
  the STMM box).
- **Permeable segment**: a vessel segment through which chemical particles
  leave the VN and reach neurons in the surrounding tissue.
- **C₁, C₂**: two chemicals whose local concentrations mark where activity
  has occurred (see the sleep cycle below).
- **V-STDP**: a plasticity rule, probably "vascular STDP"; the user notes it
  is a made-up term. Its effect is either *non-permanent* or *permanent*.
- **Short circuit current**: the joint activation of two concept assemblies,
  A and B (in the minimal version, produced by current injection).
- **Sleep cycle state**: the overall state made up of the *dream state*,
  the *recall state* and the *short circuit state*.

## Network modules (full system)

![network modules](../../archive/docs_src_dump/readme_images/network_modules.png)

The seSNN consists of three modules: R, PL and STMM.

- PL and STMM are connected by a two-way *projection*.
- PL projects into R in one direction during the *inference state*
  (*inference state projection*).
- Between PL and R the *dream state projection* runs in both directions.

## Vascular network (full system)

![vascular network](../../archive/docs_src_dump/readme_images/vn.png)
![permeable segment](../../archive/docs_src_dump/readme_images/vn_permable_segment.png)

Fluid flows through the VN from the source to the sink. Near the STMM, a
chemical gland releases chemical particles into the flow. The vessels branch
through R, with different diameters, close to the neurons and concept
assemblies. Where a vessel segment is permeable, particles leave the vessel
and reach nearby neurons.

## Sleep cycle (full system)

![sleep cycle state diagram](../../archive/docs_src_dump/readme_images/sleep_state_diagram.png)
![idealized timeline](../../archive/docs_src_dump/readme_images/sleep_timeline.png)

Take two concept assemblies, A and B, in R. The sleep cycle moves between
three states:

- **dream state → recall state** when A or B is activated;
- **recall state → dream state** when A and B are deactivated;
- **recall state → short circuit state** when a short circuit current
  occurs between A and B.

The idealized timeline runs as follows:

1. The cycle starts in the dream state. A or B is activated at random,
   which starts a recall state.
2. During each recall state there is non-permanent V-STDP, and C₁ is
   released. Dream and recall states alternate several times; in the idealized
   picture the dream phases get shorter, so the recall states follow each
   other more closely.
3. A short circuit current between A and B starts the short circuit state.
   C₂ is released, and the V-STDP is now permanent.
4. At the end of the short circuit state there is a new long-term
   association between A and B.

## Dream and recall states (full system)

![dream and recall states](../../archive/docs_src_dump/readme_images/dream_recall.png)

1. **Dream state.** One assembly (A in the figure) is activated at random;
   no activity is drawn in the STMM or the PL.
2. **Recall state.** The STMM is active. The figure shows activation
   patterns A′ and B′ in the PL, connected by arrows to the STMM and to A and
   B in R. How these interact (direction, origin of A′ and B′, what activates
   A and B) is to be specified during later development.
3. **End of the recall state.** C₁ concentrations are high around the
   neurons that fired before.

After several alternations between dream and recall, C₁ concentrations are
ideally high along one or more paths from A to B and from B to A.

## Short circuit state (full system)

![short circuit state](../../archive/docs_src_dump/readme_images/short_circuit_state.png)

At the start of the short circuit state, A, B and the neurons on the paths
between them are active, with C₁ around them. Ideally, the short circuit
current between A and B causes high C₂ concentrations only along one or more
paths from A to B and from B to A, which is the end of the short circuit
state.

## Open points

Not determined by the figures or by the user's explanation so far.

### Relevant to both the minimal version and the full system

These two are what the minimal version still has to work out (the user:
"this is kind of what needs to be figured out"), within the main criterion of
working without cheating.

- What "non-permanent" means for a weight change (duration, decay rule), and
  which thresholds and which C₁ decay are used. These are tuning parameters.
  (The number of joint activation rounds is not open in the minimal version:
  as many as needed until it works, fewer being better.)
- How V-STDP depends on the chemicals. Confirmed in outline for the minimal
  version: non-permanent changes go with C₁, permanent ones where C₁ and C₂
  are both high. The exact rule is still open (see the protocol above).

### Relevant to the full system only

- How the STMM, PL and R interact in the recall state (direction of the
  arrows, where the PL patterns A′ and B′ come from, what activates A and B).
  The user: to be specified or decided during later development.
- How C₁ and C₂ are released and carried: whether through the VN and its
  permeable segments, and which gland releases which. (The minimal version
  fixes this: release in proportion to neuron activity, at the neuron's
  location.)
- What triggers the short circuit current within the sleep cycle. (The
  electrode figure is probably minimal-version only, so the full system's
  trigger is not shown.)
- Where the short circuit state goes next (no outgoing transition is drawn).
- How the inference state relates to the sleep cycle (it appears only as a
  projection label in the module figure).
- Whether the PL has a role in the short circuit state (it is not drawn there).
