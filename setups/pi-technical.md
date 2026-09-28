# Pi host — technical

Current configuration for the dedicated always-on host (a PoE Raspberry
Pi): a general-purpose Docker-capable machine, running small always-on
services — the egress proxy the RunPod agent pod reaches over Tailscale,
and potentially other MCP servers/services alongside it. Rationale,
alternatives, and open items: `pi-rationale.md`. Why this machine exists
at all (the RunPod-side egress problem that triggered it):
`runpod-rationale.md`.

## Hardware

Already owned, capable enough that hardware is not expected to be a
limiting factor — not a purchase decision. Exact model, RAM/storage,
and PoE hat/injector not yet recorded here.

## Network

- Not yet joined to a Tailscale network.
- Not yet has a fixed address reachable from a RunPod pod.

## Software

- OS: not yet chosen.
- Docker: not yet installed. Real Docker (not the RunPod pod's
  restricted environment) is expected to work normally here — a Pi is a
  real machine with normal `CAP_NET_ADMIN`/nftables access, unlike a
  RunPod pod (see `runpod-rationale.md`'s Docker-in-Docker evidence).
- Services planned to run here: not finalized overall, but two are
  named:
  1. An egress-proxy (own instance vs. sharing this repo's existing
     `egress-proxy` config is undecided).
  2. An expanded `bridge-relay`/bridge server, giving phone-triggered
     RunPod pod spin-up an always-on trigger point independent of the
     maintainer's dev machine. Not yet designed — see
     `runpod-rationale.md`.
  Other small always-on services may follow — not yet scoped.
- Tailscale client: not yet installed.

## Credentials

- Tailscale auth key: not yet provisioned. Plan (from
  `runpod-rationale.md`): supplied to the RunPod pod via RunPod's
  `create-secret`, not hardcoded.
