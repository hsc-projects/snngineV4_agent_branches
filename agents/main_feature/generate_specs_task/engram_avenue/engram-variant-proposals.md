# Engram variant proposals

Candidate mechanisms and diagnostics drawn from the engram ideas of `engram-avenue-task.md`. Each
states its intent first; functional forms and numbers are starting points (**[default]**), and the
executing agent may use other forms or propose others (log the reason), as `agents/common.md` asks.
Nothing here is approved for an experiment: the proposals are to be revised after the Tier 1 papers are
read (step 5 of the task), then put to the user, and only then do they become a variant family of
`setups/runpod-assembly-association/sparse-assemblies-task.md` (after the engine-fix rerun). The family
letter **X** (excitability) is a suggestion; the sparse task owns its variant names.

> [!NOTE]
> **Status (2026-10-30): drafted before reading; all correspondences are the agent's reading.**

## Controls every proposal has to hold

- **Joint-activation control** of the sparse task: an association must need the co-activation of A
  and B (Faress et al. 2024 shows that a later strong event can consolidate a weak memory without
  pairing, so this control is not a formality).
- **Uniform control:** the mechanism's signal (the excitability bias) is replaced by its spatial mean.
  If the pairs associated and the strays are the same, the signal carries no spatial information. The
  uniform-C2 control of iteration 64 is the model.
- **Control 0 and control 1** as defined in the sparse task's "Terms".

## For the minimal version (sparse task)

- **X1, allocation by excitability.** *Intent:* recruit the neurons between A and B into the route by a
  transient excitability bias set by a chemical, rather than by a weight change, as allocation does
  (Yiu et al. 2014). The learning rule stays as it is (growth plus consolidation); what changes is which
  neurons fire during the joint rounds. **[default]** form: the input gain of excitatory synapses onto
  neuron i is 1 + a × C1_i / (C1_i + C_half), where C1_i is the bridge field at i's location group,
  a **[default]** 0.5, C_half the route-middle C1 of the field-geometry check; no lasting change, the
  gain follows C1. Difference from variant S4 of the sparse task: S4 scales transmission per synapse
  and damps it by the group's firing trace; X1 is a property of the neuron and is meant to be read with
  X2 and X3. *What it would show:* a route found where the substrate was silent before learning (the
  established failure of activity-proportional chemistry), with the uniform control failing. *Module
  checks:* gain 1 where C1 is 0; the gain field is bounded by 1 + a.
- **X2, competition for allocation.** *Intent:* keep the recruited set sparse: the more excitable
  neurons win and their neighbours lose, as in Rashid et al. 2016, so that strays and ignitions are
  contained without global changes that also remove transfers (iterations 61 to 63). **[default]**
  form: within each location group the bias of X1 is granted in full to the k neurons with the highest
  recent input (**[default]** k = a quarter of the group) and reduced by a factor **[default]** 0.25 for
  the others; alternative form: the bias costs fuel from the group's share (ties X2 to the E family).
  *What it would show:* X1 with X2 against X1 alone, on strays and on the ignition count at 9 × 9 × 9.
- **X3, co-allocation window.** *Intent:* the bias decays with a time constant, so joint rounds inside
  the window add up and rounds outside it do not, as memories encoded within hours link and those
  encoded days apart do not (Cai et al. 2016; Rashid et al. 2016). **[default]** form: the bias of X1
  is driven by a low-pass filtered C1 with time constant tau_x **[default]** 300 steps. *Prediction:*
  gaps between joint rounds longer than tau_x break the association. Iteration 65 found gaps irrelevant
  under the old mechanism; under X1 to X3 this becomes a falsifiable check of whether the window is real.
- **X4, silent-route diagnostic** (a measure, not a mechanism). *Intent:* tell "no route" from "route
  not retrievable", as direct optogenetic activation of engram cells does for silent engrams (Ryan et al.
  2015). *Form:* after the joint rounds, inject directly into the route neurons (those whose `w_fast`
  change exceeds a threshold, or the bridge assemblies of the sparse task) instead of into A, and test
  B. If B activates, the route exists and the failure of the A-alone test is one of retrieval (the first
  hop out of A, or the weights not yet above the single-synapse threshold); if not, no route formed.
  Candidate addition to the sparse task's tests regardless of X1 to X3.

## For the full system

- **X5, the sleep cycle as repeated encodings inside a window.** *Intent:* the dream state activates
  one assembly at random; each recall state is an encoding event; A and B become co-allocated when both
  were recalled inside the window of X3, and this co-allocation is a candidate trigger for the short
  circuit current, which the reconstruction leaves open. The idealized timeline's shortening dream
  phases would then be the window being met more and more often. *Agent's reading only*; to be specified
  with the user, who owns the full system's open points.
- **X6, two retrieval tests.** *Intent:* carry X4 into the full system: retrieval by the natural cue
  (a PL pattern projected into R) against retrieval by direct activation (current into R), so that a
  stored but silent association is detected and not counted as a failure of storage.

## What the proposals do not cover

Shared neurons between A and B (Gastaldi et al. 2021) are excluded by the minimal version's
requirements and are not proposed. If the route mechanisms keep failing, the overlap bounds of that
paper are the baseline to report against, not a variant to adopt.
