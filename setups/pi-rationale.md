# Pi host — rationale

Decisions, reasoning, alternatives rejected, and open items for the
dedicated always-on host. Current configuration: `pi-technical.md`.
Origin of this need: `runpod-rationale.md`'s egress-restriction decision
(2026-09-28) — summarized here, not repeated in full.

**Standing principle (2026-09-28, shared with `runpod-rationale.md`):
keep pieces modular/reusable rather than one-off** — applies here to how
the Pi's services (egress-proxy, bridge expansion, whatever else lands
on it) are structured: separable pieces, not one monolith.

## Decisions

**2026-09-28 — Pi helper scripts live in this repo's `setups/`, alongside
these docs.** Flashing the SD card, finding the Pi on the local network,
and running commands on it over SSH will all need repeatable tooling
(same reasoning as the sandbox project's own scripted-command convention)
rather than fleshing out each command from scratch every time. Not yet
scoped or built — needs its own explicit proposal before any script is
written, per this repo's rule against unprompted workaround scripts.

**2026-09-28 — Use a dedicated, always-on separate machine (a PoE
Raspberry Pi), not a same-pod process or a second RunPod pod.** The
RunPod agent pod has no equivalent to the local sandbox's `egress-proxy`
container split (separate network/PID namespace protecting the proxy
from the agent) — see `runpod-rationale.md` for the full comparison of
options considered (same-pod Squid+Landlock, a second RunPod pod over
public ports, routing through the maintainer's dev host) and why each
was rejected. The maintainer wants the same containment guarantees as
the local Docker sandbox in every mode (dev session or phone-only), not
a fallback that quietly weakens for the harder-to-supervise case. A
dedicated Pi restores genuine separate-machine isolation and is
maintainer-owned hardware, not a platform-dependent free tier or a
second cloud bill.

**2026-09-28 — Reached over Tailscale, not a raw public address.**
Tailscale is already used in this sandbox project for `bridge-relay`'s
inbound path, so it's an already-trusted mechanism rather than a new
one. Gives real device-level authentication instead of "public URL plus
our own bolted-on auth," which a raw exposed RunPod pod-to-pod port
would have needed.

**2026-09-28 — Scope: a general-purpose always-on host, not a
single-purpose proxy appliance.** The Pi is a real machine with normal
Docker/`CAP_NET_ADMIN`/nftables access — unlike a RunPod pod, which
can't run nested Docker at all (see `runpod-rationale.md`'s
Docker-in-Docker evidence). So it's capable of running this repo's full
local sandbox stack, not just a bare Squid instance, and is expected to
host other small always-on services (other MCP servers, etc.) alongside
the egress-proxy role that triggered building it. Renamed the component
from "Pi egress proxy" to "Pi host" to reflect this — the proxy is one
job it does, not its sole purpose.

**2026-09-28 — A cheap always-on VPS (e.g. Hetzner) was raised as a
possible alternative/fallback host and dismissed as too expensive for
just a proxy.** Not researched further, and this reasoning predates the
broader-host framing above — may be worth revisiting once the Pi's full
job list is clearer. The maintainer has an independent, unrelated
Oracle Cloud account in progress that could be revisited if a fallback
host is ever needed — not adopted here, not vetted for this purpose.

## Open items

Ordered by dependency. This list is a starting point — confirm or add to
it, it isn't guaranteed complete.

0. **Highest priority — research against our actual goals and existing
   solutions**, before any hardware/OS commitment: how people already
   run an always-on Pi as a Tailscale-reachable gateway/relay for a
   cloud workload (common homelab patterns, existing project templates),
   checked against what this specific setup actually needs (egress
   proxy + bridge-server expansion + whatever else lands on it). Point
   of this step is to avoid designing items 1+ from scratch when a
   known-good pattern already covers some or all of it.
1. **Record the existing Pi's specs.** Not a purchase decision — already
   owned, not expected to be a limiting factor. Model/RAM/storage/PoE
   hat not yet recorded here.
2. Choose OS for the Pi.
3. Enumerate the Pi's full job list — egress-proxy and the bridge
   expansion are named; "other small services like MCP servers" isn't
   further specified. Related: whether the Pi ends up running a second
   full instance of this repo's sandbox stack, or just the specific
   services it turns out to need.
4. Decide dedicated vs. shared egress-proxy instance (a new instance on
   the Pi vs. reusing the local sandbox's existing `egress-proxy`) — the
   trade-off (blast radius if the RunPod-side agent is compromised, vs.
   operational simplicity of one shared instance) hasn't been discussed.
5. Set up Tailscale on the Pi, and the auth-key provisioning path into
   the RunPod pod via `create-secret`.
6. Design the bridge-server expansion itself (which tool(s) it exposes
   for phone-triggered pod spin-up, what it needs to store) — needs its
   own explicit proposal before any code is written, per this repo's
   rule against unprompted custom scripts.
7. Physical network/location details (which LAN, PoE switch/injector
   availability) — not yet known.

Not a to-do, just a standing fact: keeping the Pi available/online when
needed is the maintainer's own responsibility, not something planned
around here — *how* (monitoring, alerting if it drops) is untouched and
may not need to be.
