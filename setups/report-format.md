# Report format

Shared convention for any findings/status report written for this
project's cloud-setup work — not a one-line status update.

**Filename:** `<task-directory-name>-report.md`, placed inside that task's
own directory (e.g. `gpu-smoke-test/gpu-smoke-test-report.md`) — not the
generic `notes.md`.

**Structure:**
- **Short summary at the top** — a few sentences: what was done, and the
  outcome (worked / worked with caveats / didn't work).
- **Subsections below it** for the details: what was actually built, how
  to run it, any hiccups hit along the way and how they were resolved (or
  not), and anything relevant for whoever picks this up next.

**Phased tasks:** when a task has quasi-independent steps/phases (a later
phase depends on an earlier one, but each is its own distinct, separately
checkable unit of work), subdivide the single report file into one
top-level section per phase, each following the summary+subsections
structure above — not one flat report covering everything.
