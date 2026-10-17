# Main Feature Specification Pipeline

This directory governs the end-to-end design and specification lifecycle for the project's main feature. To prevent conflation between exploratory drafts, actionable specifications, and long-term documentation, work is strictly partitioned into a **3-tier hierarchy**:

## 3-Tier Lifecycle

| Tier | Directory | Scope & Purpose |
| :--- | :--- | :--- |
| **Level 1: Prep Work** | `agents/main_feature/generate_specs_task/` | Exploratory research, parallel domain investigations, working drafts, and trade-off analyses required to formulate the feature specifications. |
| **Level 2: Task Specs** | `agents/main_feature/specs/` | Authoritative, actionable task specifications and implementation briefs produced by Level 1, detailing the concrete contracts for building the feature. |
| **Level 3: Final Docs** | `docs/` (root) | Formal, long-term system documentation reflecting the feature as implemented in the codebase. |

## Lifecycle Rules for Agents

1. **No direct drafting in Level 3**: The root `docs/` folder is reserved exclusively for finished, durable system documentation. Working materials or unfinalized drafts must never be placed there.
2. **Strict separation between process and deliverable**: Research, exploratory spikes, and discussion notes belong in Level 1 (`generate_specs_task/`). Completed, authoritative specification documents belong in Level 2 (`specs/`).
3. **Traceability**: Every document in Level 2 (`specs/`) must reference the underlying investigation findings in Level 1 (`generate_specs_task/`).
