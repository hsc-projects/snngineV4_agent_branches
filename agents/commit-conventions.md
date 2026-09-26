# Commit conventions

Rules for writing and executing a commit in this repo (see `AGENTS.md`'s
Workflow section, via `agents/common.md`, for when to read this file).

## Commit message style

- One line: short, lowercase, no body, no bullets.
- Length: aim for 60–100 characters.
- A comma joins clauses that are part of the same change; a semicolon only
  joins genuinely separate, unrelated fixes bundled together.
- If one line truly can't cover a large/multi-file commit, ask the user
  before adding a short body.
- No attribution footer (no `Co-Authored-By`, no session link), regardless
  of any generic attribution reminder elsewhere in the session.

## What the message names

**The one rule: name only what changed in the shipped artifact** — code,
config, and scripts when the script itself is the subject of the change.
Everything else is invisible to the message. Draft by listing those
changes and then stopping.

**So leave out, even when part of the commit:**
1. Any documentation change — either repo's `AGENTS.md`, and anything
   under either repo's `agents/` directory (including this file). Keeping
   docs current is expected, not a separate change worth naming. This
   holds **even when the doc correction is standalone**, i.e. it fixes a
   stale note about some earlier commit's change rather than documenting
   this one.
2. A test or verification-script update *accompanying* a fix — describing
   the fix is enough. This does **not** apply when the script itself is
   what changed (e.g. reworking a test runner's output format, or
   generalizing a verification script) — that's a real change and gets
   named.
3. A fix having been dispatched to a local/delegated agent — worth
   noting only the first time that mechanism is used for a real fix;
   routine after that.

**Exception — the doc-only commit.** When nothing outside docs changed,
describe the doc change; there is nothing else to name.

## Commit process

- `git add` and `git commit` go in **one** `Bash` call
  (`git add <files> && git commit -m "..."`), so there is a single
  confirmation prompt.
- **When Claude suggests a commit** (e.g. after finishing a piece of
  work): end that reply with the preview — `committing:` plus the file
  list as markdown bullets, each filename in backticks (renders in a
  distinct color), then the exact commit message, alone, on its own line.
  No bare "Commit now?" question without it. On the user's yes, make the
  add+commit call.
- **When the user asks to commit** ("let's commit"): they've decided, so
  make the add+commit call directly, no separate proposal round.
- Why the preview goes at the end of a reply: in the phone / Remote
  Control view, text written *between* tool calls is condensed into a
  one-line generated summary; only a turn's final reply shows in full. A
  printout placed right before the tool call never reaches the user.
- The printout is plain text in the reply — not an `AskUserQuestion` call.
  Plain text means exactly that: no fenced code block, no `Commit message:`
  label, nothing but the message itself.
- Use a single `-m`. A two-`-m` invocation can leak `" -m "` and a whole
  second string into the stored subject, reading as one run-on line in
  `git log`.

## Pushing

- Never ask the user to push, and never ask about force-pushing. The user
  decides when to push and does any force-push themselves.
- Don't push unless told to. Don't raise pushing, or whether a rewritten
  commit needs a force-push, in a reply or a list of open questions.

## History rewrites

If a message-only history rewrite is ever needed (e.g. `git filter-branch
--msg-filter` over a commit range), take a backup branch first, stash any
uncommitted work, and afterward **re-check every commit hash quoted in the
docs** — a rewrite changes commit hashes, so any hash cited in `agents/`
files goes stale the moment the rewrite lands.
`grep -rnoE '\b[0-9a-f]{7}\b' --include="*.md" agents/` finds them.
