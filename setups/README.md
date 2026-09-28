# Setups index

| File | What it is |
|---|---|
| `runpod-technical.md` | RunPod environment: current configuration (region, volume, pods, credentials, containment plan) |
| `runpod-rationale.md` | RunPod environment: decisions, reasoning, alternatives rejected, evidence, open items |
| `pi-technical.md` | Pi host: current configuration (hardware, network, software, credentials) |
| `pi-rationale.md` | Pi host: decisions, reasoning, alternatives rejected, open items |
| `Dockerfile-SNNgine3D-nomachine` | NoMachine remote-desktop image for SNNgine3D — outdated, not functional, kept as a starting point |
| `Dockerfile-SNNgine3D-nomachine-base` | Base image for the above — outdated, not functional, kept as a starting point |

Each `-technical.md`/`-rationale.md` pair follows this project's
design-decision-doc convention: technical files hold current state
only, rationale files hold the decisions, reasoning, and open items —
see either pair's own first lines for the cross-reference.

## External reference: the sandbox project

The RunPod/Pi containment work here (see `runpod-rationale.md` and
`pi-rationale.md`) takes inspiration from, and may reuse pieces of
(Dockerfiles, `guard-exec`'s Landlock approach, the egress-proxy setup),
a separate project: `claude-code-and-local-agent-sandbox`, at
`/home/htm/PycharmProjects/claude-code-and-local-agent-sandbox` on the
maintainer's current machine — that local path is machine-specific and
may not hold on a future machine, so treat the GitHub remote,
`github.com/hsc-projects/claude-code-and-local-agent-sandbox`, as the
durable reference (also the fallback when working from the cloud, where
no local path exists at all).
That repo builds a hardened container for running local coding agents;
its own `docker/` directory and
`docs/design/sandbox-docker-technical.md`/`-rationale.md` are the
relevant starting points. Not this project's own code — read for
reference/reuse, not treated as a dependency.
