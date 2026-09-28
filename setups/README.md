# Setups index

| File | What it is |
|---|---|
| `runpod-technical.md` | RunPod environment: current configuration (region, volume, pods, credentials, containment plan) |
| `runpod-rationale.md` | RunPod environment: decisions, reasoning, alternatives rejected, evidence, open items |
| `pi-technical.md` | Pi host: current configuration (hardware, network, software, credentials) |
| `pi-rationale.md` | Pi host: decisions, reasoning, alternatives rejected, open items |
| `Dockerfile-SNNgine3D-nomachine` | NoMachine remote-desktop image for SNNgine3D — outdated, not functional, kept as a starting point |
| `Dockerfile-SNNgine3D-nomachine-base` | Base image for the above — outdated, not functional, kept as a starting point |
| `windows/notes.md` | Windows-specific setup notes: parked research on ways to test Windows-side steps, not the primary path (see below) |
| `gpu-smoke-test/gpu-smoke-test-task.md` | Task write-up for the local GPU/CUDA-OpenGL-interop smoke test (feeds `runpod-rationale.md`'s open item 0), delegated to `agy` |
| `gpu-smoke-test/gpu-smoke-test-task-docker.md` | Task write-up for running the GPU/CUDA-OpenGL interop smoke test in a Docker container (feeds `runpod-rationale.md`'s open item 0) |
| `pi-smoke-test/task.md` | Task write-up for the Pi flash + SSH smoke test (two phases: write/flash the SD card, then SSH once the maintainer boots and connects the Pi) — not yet run |
| `report-format.md` | Shared report structure (summary + detail subsections) for findings/status reports across this project's cloud-setup work |

Each `-technical.md`/`-rationale.md` pair follows this project's
design-decision-doc convention: technical files hold current state
only, rationale files hold the decisions, reasoning, and open items —
see either pair's own first lines for the cross-reference.

## Standing principle: host-machine portability

Any Docker image, setup, or server built for this cloud-setup work must
stay testable/usable on the maintainer's actual host machine, not just on
whatever machine the work happens to be developed from. The host machine
may be a Windows laptop — don't assume Linux/Ubuntu just because
development is currently done from an Ubuntu session. Document
Windows-side instructions alongside the Linux ones as they come up, the
same as any other setup detail, without raising or discussing it each
time a Windows-specific part is added. Until a way to test those
Windows-side steps from this Ubuntu development machine is defined, mark
them as untested rather than leaving them out.

**Primary way to test Windows-side steps: WSL2 + Docker Desktop on the
maintainer's actual Windows laptop** — the real target environment, so
the most meaningful test. Whether that specific laptop can actually run
WSL2 (hardware/BIOS virtualization support, Windows edition) is
unverified as of 2026-09-28. Other options considered (GitHub Actions
`windows-latest` runners, Oracle Cloud, a Windows evaluation VM) aren't
relevant until this primary path is confirmed not to work — parked in
`windows/notes.md`, not repeated here.

Any other Windows-specific file (scripts, config, future VM assets) also
goes under `windows/`, not scattered elsewhere in `setups/`.

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
