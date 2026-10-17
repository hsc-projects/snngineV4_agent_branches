# Task: Generate Main Feature Specifications (Level 1 Prep Work)

> [!IMPORTANT]
> **Mandatory Instructions for Agents:**
> Before taking any action, reading files, or drafting content on this task, read [`agents/common.md`](file:///E:/dev/snngineV4_agent_branches/agents/common.md) (Workflow section).
> - **Do not invent claims, comparisons, or framing that were not actually said.** If any detail is underspecified, stop and ask—do not fill the gap yourself and ask afterward.
> - **Do not generalize from plausible-sounding guesses.** Stick strictly to the primary sources and what the user explicitly stated.
> - Preserving factual fidelity and the user's stated confidence level strictly takes precedence over polished prose.

## Objective

Coordinate four parallel investigation tracks to formulate, substantiate, and author the authoritative implementation specifications for the project's main feature. All deliverables feed into `agents/main_feature/specs/` (Level 2).

## The 4-Track System

### Track 1: Feature Definition ([`main-feature-definition-draft.md`](file:///E:/dev/snngineV4_agent_branches/agents/main_feature/generate_specs_task/main-feature-definition-draft.md))
- **Input**: Raw drafts and legacy documentation located in non-VCS `archive/drafts/`.
- **Role**: Ingest, understand, and rephrase what is in the drafts, adding details and technical recommendations (specifically addressing Runpod execution and engine alignment).
- **Deliverable**: Draft markdown file ([`main-feature-definition-draft.md`](file:///E:/dev/snngineV4_agent_branches/agents/main_feature/generate_specs_task/main-feature-definition-draft.md)) containing the synthesized feature definition and direct references to Track 2 and Track 3 literature digests.

### Track 2: Primary Scientific Literature (Mapped to [`agents/main_feature/main-feature-references.md`](file:///E:/dev/snngineV4_agent_branches/agents/main_feature/main-feature-references.md))
- **Input**: Papers cited by Track 1 and papers escalated from Track 3.
- **Role**: Ingest cited papers, convert them into readable, mathematically verified Markdown digests in non-VCS `archive/primary_literature/`, and map confirmed entries into [`agents/main_feature/main-feature-references.md`](file:///E:/dev/snngineV4_agent_branches/agents/main_feature/main-feature-references.md) (extending that file rather than duplicating reference lists). Holds **primary scientific facts**.
- **Storage Policy**: Detailed Markdown paper digests are strictly written to non-VCS `archive/primary_literature/`. Canonical entries and citations are added to [`agents/main_feature/main-feature-references.md`](file:///E:/dev/snngineV4_agent_branches/agents/main_feature/main-feature-references.md) and cited in [`main-feature-definition-draft.md`](file:///E:/dev/snngineV4_agent_branches/agents/main_feature/generate_specs_task/main-feature-definition-draft.md).
- **Items**:
  - [low] Nageswaran, Dutt, Krichmar, Nicolau, Veidenbaum. "A configurable simulation environment for the efficient simulation of large-scale spiking neural networks on graphics processors." *Neural Networks*, 2009. ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0893608009001373)) — Extended journal version of the Nageswaran et al. IJCNN 2009 paper already in `agents/main_feature/main-feature-references.md`. Confirmed by user to be in personal library; review for applicable algorithmic details.

### Track 3: Exploratory Literature & Citation Traversal (Referenced in [`main-feature-definition-draft.md`](file:///E:/dev/snngineV4_agent_branches/agents/main_feature/generate_specs_task/main-feature-definition-draft.md#L20-L24))
- **Role**: Research, read, and digest papers in an exploratory manner, including readouts of papers cited by Track 2 papers. Holds **secondary and exploratory knowledge**.
- **Escalation Funnel**: If an exploratory paper in Track 3 is found to be highly relevant, it is promoted to Track 2 and added to [`agents/main_feature/main-feature-references.md`](file:///E:/dev/snngineV4_agent_branches/agents/main_feature/main-feature-references.md).
- **Storage Policy (Non-VCS)**: Markdown digests are strictly written to `archive/exploratory_literature/` outside of Git.
- **Items**:
  - [low] Comparative architecture research: Compare snngineV4's config→template→build pattern (see [`agents/mapping/config-build-pattern.md`](file:///E:/dev/snngineV4_agent_branches/agents/mapping/config-build-pattern.md)) against established patterns used by other 3D/game engines for config-driven object construction feeding a rendering/simulation loop.

### Track 4: Meta-Research & Methodology ([`research-synthesis-methodology.md`](file:///E:/dev/snngineV4_agent_branches/agents/main_feature/generate_specs_task/research-synthesis-methodology.md))
- **Role**: Centralizes the operational research, digest formatting, and synthesis methodology used across Tracks 1, 2, and 3.
- **Working Files & Non-VCS Staging**:
  - Ratified methodology document: [`research-synthesis-methodology.md`](file:///E:/dev/snngineV4_agent_branches/agents/main_feature/generate_specs_task/research-synthesis-methodology.md) (in Git).
  - Raw methodology source dumps: `archive/methodology/dumps/` (non-VCS).
  - Methodology change proposals: `archive/methodology/proposals/` (non-VCS).

## Rules & Boundaries for Agents

1. **Non-VCS Boundary**: Paper digests, raw drafts, and methodology dumps/proposals reside strictly in `archive/` (gitignored) and are only referenced by path. Never commit paper digests to Git.
2. **Knowledge Boundary**: Primary scientific facts (Track 2) and secondary/exploratory knowledge (Track 3) remain distinct in `archive/` and within the references in [`main-feature-definition-draft.md`](file:///E:/dev/snngineV4_agent_branches/agents/main_feature/generate_specs_task/main-feature-definition-draft.md).
3. **Escalation**: When a paper in Track 3 is found to be foundational or directly relevant to the feature mechanisms, promote it to Track 2.
