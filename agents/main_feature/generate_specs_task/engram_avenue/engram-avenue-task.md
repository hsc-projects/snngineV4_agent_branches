# Task: Engram Avenue for the Main Feature (Level 1 investigation)

> [!NOTE]
> **Status (2026-10-30): proposed by the agent, approved by the user as an avenue to explore; not started.**
> Literature and concept work only, no code and no pods. Nothing in this folder is a finding yet:
> the papers have not been read in this project, and every claim about them is marked
> *verified* (citation and abstract checked online on 2026-10-30), *from memory* (to verify in step 1),
> or *agent's reading* (an interpretation, to check against the paper). **[default]** marks a
> starting value the executing agent may change (log the reason).

> [!IMPORTANT]
> **Read first:** the Workflow section of `agents/common.md`; `agents/main_feature/README.md` (the
> 3-tier pipeline; this folder is Level 1, Track 3 with escalation to Track 2);
> `agents/main_feature/main-feature-readme-reconstruction.md` (the concept, minimal version and full
> system); `setups/runpod-assembly-association/assembly-association-glossary.md` (the rule for
> established terms, and the plasticity terms already mapped); the "Terms" and "Variants" sections of
> `setups/runpod-assembly-association/sparse-assemblies-task.md`; the entry N9 (Faress et al. 2024) in
> `archive/unsorted_literature/assembly_association_papers_ranking.md`. Do not invent claims about the
> concept; if something is underspecified, ask the user.

## Why

The minimal version and its successor (the sparse-assemblies task) have hit these problems (results of
the faulty engine, to be re-established by `setups/runpod-assembly-association/engine-fix-rerun-task.md`,
but the questions stand): activity-proportional chemistry cannot select a route that is silent before
learning; C2 carries no spatial information (the uniform-C2 control associates the same pairs);
propagation is all-or-none, and every change that removed ignitions also removed most transfers.

The engram literature studies how a memory is assigned to a set of neurons, how two memories formed
close in time become linked, and how a memory can exist without being retrievable. The project's
literature so far (142 digested papers, the 72-paper ranking, the two later search rounds) contains
none of this line; the word appears only in passing in three digests (Faress et al. 2024, Lehr et al.
2022, Fiebig and Lansner 2014). Faress et al. 2024 is the nearest existing entry and the starting point.

## Question

Does the engram literature offer mechanisms or criteria for

1. the **minimal version**: selecting the route between A and B (recruitment of the neurons between
   them), containing strays and ignitions, and the distinction between a path that exists and a path
   that is retrievable by activating A alone;
2. the **full system**: the dream and recall alternation of the sleep cycle, consolidation in the short
   circuit state, and the interplay of R, PL and STMM?

The four engram ideas to test against these questions (all *verified* at abstract level):

- **Allocation by excitability.** Neurons with higher excitability just before training are
  preferentially recruited into the memory (Yiu et al. 2014). The recruiting signal is a transient
  excitability bias, not a weight change.
- **Co-allocation within a time window.** Two memories encoded close in time (hours) share neurons
  and become linked; encoded far apart (days) they do not; the link depends on excitability
  (Cai et al. 2016; Rashid et al. 2016, with competition between engrams).
- **Silent engrams.** A memory can be stored (the cells and their connectivity exist) but not be
  retrievable by the natural cue, while direct activation of the cells retrieves it (Ryan et al. 2015).
- **Engram complex.** One memory is held by connected ensembles across many regions (Roy et al. 2022).

A fifth, as a contrast rather than a model: association through *shared* neurons between two engrams,
with a minimal and a maximal overlap fraction (Gastaldi et al. 2021). The minimal version excludes
shared neurons by construction (A and B know nothing of each other), so this paper bounds what our
mechanism must achieve without overlap.

## Scope

- Both versions of the main feature, minimal and full.
- Literature (Track 3 digests, escalation to Track 2), concept mapping, and variant proposals.
- **Out of scope:** code, pod runs, and changes to the running tasks (`sparse-assemblies-task.md`,
  `rate-model/`, `engine-fix-rerun-task.md`). An experiment comes later, as a new variant family in the
  sparse task after the rerun, if the user approves the proposals.

## Deliverables

1. `engram-concept-mapping.md`: our terms against engram terms, each marked **same**, **partial** or
   **own**, with the paper the definition is taken from and how our usage differs. Entries that hold up
   are proposed for `assembly-association-glossary.md` and `agents/glossary.md` (the user approves).
2. `engram-literature-ranking.md`: the papers, tiered by expected use, in the format of
   `archive/unsorted_literature/assembly_association_papers_ranking.md`; "Why" and "Look for" before
   reading, "Finding" after.
3. Digests in non-VCS `archive/exploratory_literature/engram/` (PDF plus Markdown version, as in
   `archive/primary_literature/`). Papers found foundational are promoted: digest moved to
   `archive/primary_literature/`, entry added to `agents/main_feature/main-feature-references.md`
   (propose, the user approves).
4. `engram-variant-proposals.md`: candidate mechanisms, intent first, forms and numbers as
   **[default]**, with the controls each needs; one section for the sparse task, one for the full system.
5. A closing section in this file ("Outcome"): which of the four ideas map onto an open problem,
   which do not, and the stop-rule decision.

## Steps

1. **Citations and PDFs.** Verify every entry marked *from memory* in the ranking (venue, year, volume,
   DOI). Collect the PDFs: on 2026-10-30 none of the engram papers was in `E:\MEGA\Mendeley Library`
   or in `archive/` (matched by title), so ask the user, or fetch open-access copies into
   `archive/exploratory_literature/engram/` as was done in
   `archive/unsorted_literature/non_mendeley_downloads/`.
2. **Read Tier 1** (**[default]** the seven papers of Tier 1, the review first), digest each, and replace
   the "Why / Look for" of its ranking entry by a "Finding" from the paper, as the existing ranking does.
3. **Fill the concept mapping** from what was read. Keep our terms where the fit is partial.
4. **Rank Tier 2 and 3** again against the findings; read what the findings make relevant.
5. **Write the variant proposals**, each with its uniform control: a mechanism that works equally well
   when its signal is made spatially uniform carries no spatial information (the uniform-C2 result).
6. **Outcome and stop rule** (below); propose the glossary additions and the escalations to Track 2.

## Stop rule

Drop the avenue only if, after step 2, none of the four ideas maps onto an open problem of the
minimal version or the full system beyond what the existing variant families (S, L, K, E of the
sparse task) already cover. Before dropping, try the other reading of each idea (for example,
excitability as a use of C1 against excitability as a use of the fuel C3), as `agents/common.md`
asks. Record the decision and its reason in "Outcome".

## Rules

1. **Confinement.** Files of this task live in this folder and in non-VCS
   `archive/exploratory_literature/engram/`. Do not modify sibling task folders under `setups/` or the
   other files of `generate_specs_task/`; propose changes to glossaries, references and
   `agents/feature-todos.md` to the user instead.
2. **Terms.** Our terms take priority where the fit is partial (`assembly-association-glossary.md`,
   rule at the top). "Engram" does not replace "concept assembly": our assemblies are imposed by
   position; an engram is defined by the neurons active at encoding and needed for recall.
3. **Fidelity.** Keep the three markers (*verified*, *from memory*, *agent's reading*) until a paper is
   read; a read paper's entry states what the paper found, with the user's and the agent's readings kept
   apart.
4. **VCS.** No commits or pushes without the user's go. Digests never enter Git.
5. **Cost.** None (no pods).

## Outcome

*(empty until step 6)*
