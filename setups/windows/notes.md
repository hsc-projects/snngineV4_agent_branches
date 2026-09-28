# Windows-side testing alternatives — research notes

This file: not decided, not pursued further, nothing downloaded. Written
down so the research from 2026-09-28 isn't lost, not as an active plan.
Primary way to test Windows-side setup steps stays WSL2 + Docker Desktop
on the maintainer's actual Windows laptop (see `../README.md`).

The `windows/` folder itself is general-purpose: any Windows-specific
file (notes, scripts, config, future VM assets) for this cloud-setup work
belongs here, not just this one research topic. It's gitignored for
anything beyond markdown (a VM disk image or ISO would be several GB and
must never land in git) — see the repo's `.gitignore`.

## Why this came up

RunPod pods don't support Windows at all (`docs.runpod.io/pods/overview`,
checked 2026-09-28: "Windows is not supported"). That's about the RunPod
GPU pod itself, unrelated to this file — but it's what surfaced the
broader question of how to test the *host laptop's* Windows-side
instructions (WSL2 + Docker) from a Linux dev machine when the laptop
itself isn't at hand.

## Alternatives surveyed, host-agnostic (no VM/download needed)

- **GitHub Actions `windows-latest` runners.** Free, Docker with Linux-
  container support (WSL2 backend) preinstalled, automatable from any
  Linux host without touching real hardware. **Cannot cover this
  project's GPU smoke tests** — GitHub-hosted Windows runners have no
  GPU, so this only reaches CPU-only setup/Docker steps.
- **AWS Free Tier.** Checked 2026-09-28 (`aws.amazon.com/free`): AWS
  changed its free tier to a $200-credit-over-6-months model for new
  accounts, not the older "12 months of a free t2/t3.micro" scheme.
  Windows EC2 would draw down that credit like anything else, not run
  free indefinitely.
- **Oracle Cloud's Always Free tier.** Checked 2026-09-28
  (`docs.oracle.com`, Always Free Resources page): Always Free compute
  shapes are AMD Micro (`VM.Standard.E2.1.Micro`) or Ampere A1/ARM
  (`VM.Standard.A1.Flex`) only. No Windows image is documented as
  Always-Free-eligible, and Windows Server on OCI normally carries its
  own per-OCPU licensing charge on top of compute. Likely not actually
  free — ruled out unless that cost question gets resolved.

## The Windows evaluation VM option

**Fact, verified 2026-09-28** (`microsoft.com/en-us/evalcenter/evaluate-windows-11-enterprise`):
Microsoft publishes free, full-featured evaluation ISOs (e.g. Windows 11
Enterprise, version 25H2) — pre-activated, no product key needed at
install, licensed for a 90-day evaluation. Could run as a VM on this
Linux host (VirtualBox or QEMU/KVM), with WSL2 + Docker tested inside
that guest via nested virtualization.

**How the 90-day limit is enforced** (general Windows evaluation-licensing
behavior — not verified against a specific Microsoft document beyond the
evalcenter page above, so treat the mechanism as reasonably confident but
not confirmed line-by-line): not a hard lockout. Past 90 days without
extending, Windows drops into "notification mode" — a persistent desktop
watermark, periodic forced restarts, black desktop background — while the
OS (and Docker/WSL2 inside it) keeps functioning. Extendable a limited
number of times via the built-in `slmgr /rearm` command, each resetting
the 90-day clock.

**Assumption, unconfirmed:** nothing technically stops downloading a
fresh ISO and building a new VM once `/rearm` extensions run out — each
fresh install gets its own new evaluation clock. Not verified against
Microsoft's evaluation EULA text (not read in full this session); likely
fine for genuine internal/periodic testing (which this is), since that's
what an evaluation license is for, but arguably against the "evaluation
purposes" framing if leaned on as a permanent substitute for a real
license — not something to treat as durable infrastructure.

**Not checked at all (real blockers, not yet cleared):**
- Whether this specific Ubuntu host actually supports nested
  virtualization (CPU VT-x/AMD-V flags, KVM `nested` kernel module
  parameter) — reading that host state is outside this repo's
  allowed-touch boundary (`AGENTS.md` in the sandbox project), so it
  needs the maintainer's approval before even checking.
- The ISO's exact current download size (multi-GB; not measured).
  Downloading it would also need an explicit one-off exception to the
  host session's fetch-tool-only web policy (`mcp__fetch__fetch` can't
  carry a file this large), the same kind of exception given previously
  for local-model downloads.
- Scripting an unattended Windows install (no GUI available here to
  click through setup manually) — not attempted, not scoped.

**Net assessment:** a real alternative in principle, but meaningfully
more setup/fragility than either the real laptop or the GitHub Actions
option above — ranked behind both. Revisit only if the laptop path turns
out not to work (e.g. that specific hardware can't run WSL2) and a real
Windows-behavior test (not just CPU-only CI) is still needed.
