# Engram literature ranking

Ranks the engram papers by their expected use for the main feature, in the format of
`archive/unsorted_literature/assembly_association_papers_ranking.md`. Variants X1 to X5 are the
proposals of `engram-variant-proposals.md`.

> [!NOTE]
> **Status (2026-10-30): drafted before reading; no paper is Read.** Status column: *Verified* (citation
> and abstract checked online on 2026-10-30; the Yiu entry by title and citation only), *From memory*
> (authors, year, venue and title as recalled by the agent; volume, pages and DOI to be verified in
> step 1 of the task, and the entry corrected or dropped if it does not exist as stated), *Read* (digest in
> `archive/`). "Why" and "Look for" are expectations from titles and abstracts, not findings; replace them
> by a "Finding" once the paper is read. **Availability (2026-10-30):** none of these papers is in
> `E:\MEGA\Mendeley Library` or in `archive/` (matched by title), except Faress et al. 2024
> (`archive/primary_literature/`, entry N9 of the existing ranking).

## State of the task the ranking is judged against

As of 2026-10-30: the results of iterations 1 to 65 and SP0 to SP3 came from the faulty engine and
are being re-established (`setups/runpod-assembly-association/engine-fix-rerun-task.md`). The open
problems the ranking is judged against are those listed under "Why" in `engram-avenue-task.md`.

## Evaluation criteria

1 to 5 as in the existing ranking (propagation across distance; route selection and consolidation;
focusing and containment; association and recall; spatial wiring and reach), plus:

6. **Full system:** the sleep cycle (dream, recall, short circuit states), its trigger, and the
   interplay of R, PL and STMM.

## Tier 1: read first

| # | Paper | Status | Criteria / variants | Why; look for |
|---|---|---|---|---|
| 1 | Josselyn, Tonegawa, 2020, *Memory engrams: recalling the past and imagining the future*, Science 367(6473), eaaw4325 | Verified | all; entry point | Review of the field: evidence for engrams, the roles of intrinsic excitability and synaptic plasticity, lifetime, open questions. Look for: the operational definition (sufficiency and necessity), how excitability and synaptic change are weighed, and what is said about linking and about silent engrams. |
| 2 | Yiu et al., 2014, *Neurons are recruited to a memory trace based on relative neuronal excitability immediately before training*, Neuron 83, 722–735 | Verified (title, citation) | 2; X1 | The allocation-by-excitability result. Look for: how excitability was raised or lowered, the size of the recruitment bias, how long before training it acts, and whether the bias is relative (competition) or absolute. |
| 3 | Rashid et al., 2016, *Competition between engrams influences fear memory formation and recall*, Science 353(6297), 383–387 | Verified (abstract) | 2, 3; X2, X3 | Lateral amygdala: more excitable neurons outcompete neighbours for allocation; a transient competitive process links events close in time (co-allocation) and separates distal ones. Look for: the window, what mediates the competition (inhibition?), and what happens to engram size. |
| 4 | Cai et al., 2016, *A shared neural ensemble links distinct contextual memories encoded close in time*, Nature 534(7605), 115–118 | Verified (abstract) | 4; X3 | CA1 ensembles of two contexts overlap more when learned within a day than a week apart; aged mice with lower excitability lack the overlap, and raising excitability rescues linking. Look for: whether linking needs the overlap, the time course, and the overlap fractions. |
| 5 | Ryan et al., 2015, *Memory engram cells retain memory under retrograde amnesia*, Science 348(6238), 1007–1013 | Verified (abstract) | 4; X4 | Silent engrams: storage kept in the cells' connectivity while the natural cue fails; direct activation retrieves; consolidation-related synaptic strengthening missing. Look for: what "connectivity-based storage" measures, and what retrieval by direct activation needs. |
| 6 | Gastaldi, Schwalger, De Falco, Quian Quiroga, Gerstner, 2021, *When shared concept cells support associations: theory of overlapping memory engrams*, PLoS Comput Biol 17(12), e1009691 | Verified | 4 (contrast) | Attractor-network theory: minimal and maximal overlap fractions for association with separate recall; association chains under a periodically modulated background. Look for: the bounds, the recall dynamics under oscillation (the recall state of the full system?), and the model's assumptions that our minimal version violates (shared neurons). |
| 7 | Faress et al., 2024, *Non-Hebbian plasticity transforms transient experiences into lasting memories* | Read (N9, `archive/primary_literature/`) | 2 | Already digested for the K variants: a later strong event consolidates a weak memory without pairing; every mechanism must hold the joint-activation control. Reread for what it says about allocation and engram cells. |

## Tier 2: likely to help

| # | Paper | Status | Criteria / variants | Why; look for |
|---|---|---|---|---|
| 8 | Roy et al., 2022, *Brain-wide mapping reveals that engrams for a single memory are distributed across multiple brain regions*, Nat Commun 13, 1799 | Verified | 6 | The unified engram complex: functionally connected ensembles across regions. Look for: how connection between regional engrams was shown; an analogy for R, PL and STMM. |
| 9 | Kitamura et al., 2017, *Engrams and circuits crucial for systems consolidation of a memory*, Science | From memory | 6 | Prefrontal engram cells formed at encoding, silent at first, matured over days while hippocampal ones de-matured. Look for: the time course and the role of reactivation during consolidation (the sleep cycle). |
| 10 | Han et al., 2007, *Neuronal competition and selection during memory formation*, Science | From memory | 2; X1, X2 | CREB levels bias which lateral amygdala neurons join the memory. Look for: the competitive selection and its size. |
| 11 | Zhou et al., 2009, *CREB regulates excitability and the allocation of memory to subsets of neurons in the amygdala*, Nat Neurosci | From memory | 2; X1 | The link from CREB to excitability to allocation. Look for: the excitability measure and its time course. |
| 12 | Lisman, Cooper, Sehgal, Silva, 2018, *Memory formation depends on both synapse-specific modifications of synaptic strength and cell-specific increases in excitability*, Nat Neurosci | From memory | 2; X1, X3 | The conceptual bridge between synapse-level tagging (already in the glossary) and cell-level allocation. Look for: how the two interact, and the proposed time scales. |
| 13 | Kastellakis, Silva, Poirazi, 2016, *Linking memories across time via neuronal and dendritic overlaps in model neurons with active dendrites*, Nat Commun | From memory | 4; X3 | A computational model of memory linking through excitability and shared neurons or dendrites. Look for: the model's window and what it needs beyond point neurons. |
| 14 | Tomé et al., 2024, *Dynamic and selective engrams emerge with memory consolidation*, Nat Neurosci | From memory | 2, 6 | Computational model (Clopath group) of engram selection and change during consolidation. Look for: the role of inhibition and of reactivation. |
| 15 | Josselyn, Köhler, Frankland, 2015, *Finding the engram*, Nat Rev Neurosci | From memory | all | Earlier review; the criteria for an engram. |
| 16 | Tonegawa, Liu, Ramirez, Redondo, 2015, *Memory engram cells have come of age*, Neuron | From memory | all | Earlier review from the other main group. |

## Tier 3: background

| # | Paper | Status | Criteria / variants | Why; look for |
|---|---|---|---|---|
| 17 | Abdou et al., 2018, *Synapse-specific representation of the identity of overlapping memory engrams*, Science | From memory | 4 | Two memories sharing engram cells are kept apart at the level of synapses. Look for: what distinguishes them when the cells overlap. |
| 18 | Silva, Zhou, Rogerson, Shobe, Balaji, 2009, *Molecular and cellular approaches to memory allocation in neural circuits*, Science | From memory | 2 | Review of allocation. |
| 19 | Sehgal et al., 2018, *Memory allocation mechanisms underlie memory linking across time*, Neurobiol Learn Mem | From memory | 4; X3 | Short review tying allocation to linking. |
| 20 | Ramsaran et al., 2023, *A shift in the mechanisms controlling hippocampal engram formation during brain maturation*, Science | From memory | 3 | Engram size and sparsity set by inhibition (parvalbumin interneurons) during development. Look for: the containment mechanism. |
