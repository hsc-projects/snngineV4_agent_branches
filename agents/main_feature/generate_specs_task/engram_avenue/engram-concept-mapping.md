# Engram concept mapping

Maps the terms of the main feature (`agents/main_feature/main-feature-readme-reconstruction.md`) and of
the assembly-association work to the terms of the engram literature. Same rule as
`setups/runpod-assembly-association/assembly-association-glossary.md`: use the established term where it
means the same thing; where it does not, keep our term (**own**) and do not bend the idea to the
vocabulary; mark a partial fit **partial**. Synapse-level terms (early and late phase, tag, capture,
consolidation) are already mapped there and are not repeated.

> [!NOTE]
> **Status (2026-10-30): drafted before reading.** Every definition below is at abstract level
> (*verified*: citation and abstract checked online on 2026-10-30) or *from memory* (to verify), and every
> correspondence is the *agent's reading*, to be confirmed or corrected against the papers in step 3 of
> `engram-avenue-task.md`. Nothing here is an established equivalent yet.

## Ensembles

- **Concept assembly** → *engram*, *engram cells* (**partial**). An engram is the set of neurons active
  during encoding whose reactivation is sufficient, and whose silencing is detrimental, for recall
  (Josselyn and Tonegawa 2020, review; *verified*). Ours is imposed by position (a location group with
  boosted intra-group input), not selected by encoding; it stands in for an engram, it is not one formed
  by learning. Keep "concept assembly".
- **Ordinary neurons on the route** → *allocated neurons*, *engram cells recruited at encoding*
  (**partial**, *agent's reading*). In allocation studies the recruited neurons are those with higher
  excitability just before training (Yiu et al. 2014; *verified*). The route neurons between A and B are
  what the minimal version has to recruit; whether an excitability bias can do it is proposal X1 of
  `engram-variant-proposals.md`.
- **Strays, ignition** → *engram size*, *competition between engrams* (**partial**, *agent's reading*).
  Rashid et al. 2016 (*verified*): neurons with higher excitability outcompete their neighbours for
  allocation, which keeps the engram sparse. Our strays are assemblies recruited beside the route;
  ignition is spread over much of the reservoir. The competitive process is a candidate containment
  mechanism (proposal X2).

## Linking and time

- **Joint activation rounds, co-activation** → *co-allocation*, *memory linking* (**partial**). Two
  memories encoded within hours share a larger fraction of neurons and become linked, so that recall of
  one triggers the other; encoded a week apart they do not (Cai et al. 2016, hippocampal CA1; Rashid et
  al. 2016, lateral amygdala; both *verified*). Differences: there, two distinct memories are linked
  through shared neurons; here, two existing assemblies with no shared neurons are to be linked through
  a route. The time window (hours, set by the decay of the excitability bias) has no counterpart yet in
  our protocol, whose rounds are tens of steps apart (proposal X3).
- **Dream and recall alternation (full system)** → *time window of co-allocation* (**own**, *agent's
  reading*). The sleep cycle's alternation between random activation of one assembly and recall could
  play the role of repeated encodings inside the window. The reconstruction leaves the trigger of the
  short circuit current open; the engram window is a candidate for it. Keep our terms.
- **Association through a route** against *association through overlap* (**contrast**, not a mapping).
  Gastaldi, Schwalger, De Falco, Quian Quiroga and Gerstner 2021 (*verified*) give, in an attractor
  network, a minimal fraction of shared neurons below which associations cannot be implemented and a
  maximal fraction above which separate recall breaks down. The minimal version forbids shared neurons
  (A and B know nothing of each other), so our mechanism has to supply, through the route, what overlap
  supplies there. Useful as a bound and as a baseline to compare against, not as a model of ours.

## Storage against retrieval

- **A path exists but A alone does not activate B; `w_fast` against `w_perm`** → *silent engram*
  (**partial**). Ryan et al. 2015 (*verified*): under protein-synthesis inhibition the engram cells keep
  their connectivity-based storage, the natural cue fails, and direct optogenetic activation of the
  cells retrieves the memory; the increase of synaptic strength and spine density seen after
  consolidation is missing. Our transfer test (inject A alone) is the natural cue; injecting the route
  neurons directly would be the optogenetic analogue (proposal X4, a diagnostic, not a mechanism).
- **Short circuit stage, consolidation under C2** → *engram consolidation*, *systems consolidation*
  (**partial**; *from memory*: Kitamura et al. 2017, engrams and circuits for systems consolidation).
  Theirs moves the memory between regions over days; ours moves `w_fast` into `w_perm` on one route.

## Modules (full system)

- **R, PL and STMM holding one association** → *unified engram complex* (**partial**, *agent's
  reading*). Roy et al. 2022 (*verified*): one memory is held by functionally connected engram ensembles
  across many brain regions. An analogy for the module structure of the full system, not a design.

## Signals

- **C1 as a recruiting signal** → *excitability bias at encoding*; *CREB-dependent allocation*
  (**partial**, *agent's reading*; the CREB mechanism *from memory*: Han et al. 2007, Zhou et al. 2009).
  The engram literature's recruiting signal raises the excitability of the neurons that will join;
  our C1 so far gates weight changes. The reinterpretation of C1 (or of the fuel C3) as an excitability
  modulator is proposal X1; the glossary already lists diffusing modulation of excitability (GasNets,
  Sweeney et al. 2015) under C3.
- **C2** has no engram-level counterpart found so far; it stays mapped to the neuromodulator of the
  tagging-and-capture literature (`assembly-association-glossary.md`).
