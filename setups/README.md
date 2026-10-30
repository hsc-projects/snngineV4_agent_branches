# Setups index

| File | What it is |
|---|---|
| `runpod-technical.md` | Runpod environment: current configuration (region, volume, pods, credentials, containment plan) and how to run and collect pod sessions |
| `runpod-rationale.md` | Runpod environment: decisions, reasoning, alternatives rejected, evidence, open items |
| `pi-technical.md` | Pi host: current configuration (hardware, network, software, credentials) and how to operate it (flash, reach, sharing, pitfalls) |
| `pi-rationale.md` | Pi host: decisions, reasoning, alternatives rejected, open items; its last block, "Where things stand", is where a new session starts |
| `Dockerfile-SNNgine3D-nomachine` | NoMachine remote-desktop image for SNNgine3D — outdated, not functional, kept as a starting point |
| `Dockerfile-SNNgine3D-nomachine-base` | Base image for the above — outdated, not functional, kept as a starting point |
| `windows/notes.md` | Windows-specific setup notes: parked research on ways to test Windows-side steps, not the primary path (see below) |
| `gpu-smoke-tests/gpu-smoke-test-task.md` | Task write-up for the local GPU/CUDA-OpenGL-interop smoke test (fed `runpod-rationale.md`'s open item 0, resolved 2026-10-15), delegated to `agy` |
| `gpu-smoke-tests/gpu-smoke-test-report.md` | Execution report for local standalone workstation GPU/CUDA-OpenGL zero-copy interop smoke test (RTX 3090, 5-link chain) |
| `gpu-smoke-tests/gpu-smoke-test-task-docker.md` | Task write-up for running the GPU/CUDA-OpenGL interop smoke test in a Docker container (fed `runpod-rationale.md`'s open item 0, resolved 2026-10-15) |
| `gpu-smoke-tests/gpu-smoke-test-report-docker.md` | Execution report for containerized GPU/CUDA-OpenGL zero-copy interop smoke test (Docker, headless EGL, WebSocket web bridge) |
| `gpu-smoke-tests/gpu-smoke-test-task-v2.md` | Task write-up for modernizing the GPU/CUDA-OpenGL interop stack across all 3 modes (EGL, Desktop GUI, Web Bridge) at max RTX 3090-compatible versions |
| `gpu-smoke-tests/gpu-smoke-test-report-v2.md` | Execution report for modernized max-frontier GPU/CUDA-OpenGL interop stack (Python 3.14, CUDA 13.2, PyTorch 2.15 dev) |
| `runpod-smoke-tests/runpod-smoke-test-task.md` | Task write-up for the Runpod cloud GPU/CUDA-OpenGL interop smoke test (fed `runpod-rationale.md`'s open item 0, resolved 2026-10-15) |
| `runpod-smoke-tests/runpod-smoke-test-report.md` | Execution report and zero-copy pointer verification for Runpod cloud GPU/CUDA-OpenGL interop smoke test |
| `runpod-engine-smoke-test/runpod-engine-test-task.md` | Task write-up for the Runpod headless simulation engine smoke test (feeds domain simulation validation on cloud GPU) |
| `runpod-engine-smoke-test/runpod-engine-smoke-test-report.md` | Execution report for Runpod headless simulation engine smoke test (100-step execution, resting membrane stability) |
| `runpod-engine-smoke-test/runpod-engine-video-task.md` | Task write-up for Runpod headless simulation video generation and 3-panel composite telemetry |
| `runpod-engine-smoke-test/runpod-engine-video-report.md` | Execution report and performance benchmarks for Runpod headless simulation video generation and 3-panel composite telemetry |
| `runpod-chem-diffusion/runpod-chem-diffusion-task.md` | Task write-up for Runpod headless 3D chemical source and volumetric diffusion video generation |
| `runpod-chem-diffusion/runpod-chem-diffusion-report.md` | Execution report and quantitative diffusion telemetry for Runpod 3D chemical source and volumetric diffusion video generation |
| `runpod-assembly-association/runpod-assembly-association-task.md` | Task write-up for the minimal version of the main feature: two assemblies associated through activity-proportional chemical release and chemical-gated plasticity, implemented and tuned on Runpod in a cost-efficient loop |
| `runpod-assembly-association/archive-pre-engine-fix/README.md` | Results produced on the faulty engine (before 2026-10-30): the minimal-version report and tuning logs (iterations 1 to 65), the sparse report and log (SP0 to SP3), session parameter files, rate-model rounds 1 to 5; a record, not evidence |
| `runpod-assembly-association/sparse-assemblies-task.md` | Successor task: sparse assemblies on distance-dependent wiring, with route selectivity and controls for each chemical field (variants S, L, K, E); SP0 to SP3 ran on the faulty engine (archived), continues after the rerun |
| `runpod-assembly-association/assembly-association-glossary.md` | Our terms of the assembly-association work mapped to established terms in the literature, with sources |
| `runpod-assembly-association/engine-fix-rerun-task.md` | Rerun task after the engine fixes of 2026-10-30: which experiments and conclusions rested on the synapse-table transpose and the other engine bugs, and the rerun order (build audit, wiring decision, regime, propagation, protocol, grid comparison, sparse substrate); in progress, steps 0 and 1 done, step 2 waits for the wiring decision (`engine-fix-rerun-report.md`) |
| `runpod-assembly-association/rate-model/rate-model-task.md` | Task write-up for a cheap group-level model to screen parameters before spiking runs; rounds 1 to 5 (archived) admitted no model, round 6 traced the disagreement to the engine's transposed synapse table |
| `runpod-engine-benchmark/runpod-engine-benchmark-task.md` | Task write-up for checking the engine's correctness against analytic cases and a CPU reference, and benchmarking construction, engine and harness steps on a reference GPU (proposed) |
| `runpod-engine-tests/README.md` | Running the engine's test suite (`snngine_v4/tests/`) on a Runpod GPU pod on a packed copy of the code (never the shared volume's code or build): pack, run, collect; `engine-tests-report.md` holds one entry per run |
| `runpod_find_combos.py` | Query live Runpod GraphQL API for in-stock, cost-optimal GPU/CPU options matching network volume constraints |
| `.secrets/.env` | Gitignored credentials (e.g. `RUNPOD_API_KEY`) read at runtime by host tools |
| `pi-smoke-test/task.md` | Task write-up for the Pi flash + SSH smoke test (two phases: write/flash the SD card, then SSH once the maintainer boots and connects the Pi) — done 2026-10-04, kept current |
| `pi-smoke-test/pi-smoke-test-report.md` | Evidence and findings of that smoke test, plus the Proton VPN and first-boot follow-ups |
| `pi-smoke-test/pi_smoke_test_flash.py`, `pi_smoke_test_ssh_check.py` | Flash/configure an SD card (Linux and Windows) and find/SSH into the Pi |
| `pi-provision/pi-firstboot.sh` | Script that runs on the Pi's first boot (installed by the flash script through cloud-init, retried until done): WireGuard, the credential stick, the tunnel at boot, stick hotplug recovery, Docker, git, the `claude` user, the keyholder, Tailscale (with identity restore), the Wi-Fi password scrub; tested on fresh flashes |
| `pi-provision/tailscale-policy.hujson` | The tailnet access policy for the Pi (paste into the Tailscale admin console) |
| `pi-provision/push_wireguard_config.py` | Pushes the Proton WireGuard config to the Pi's credential stick over SSH |
| `pi-provision/pi_keyholder.py` | Laptop client for the Pi's keyholder: add an encrypted secret, unlock it into the Pi's RAM, lock, status |
| `pi-stolen-checklist.md` | What to revoke if the Pi, its card or its credential stick is lost or stolen |
| `windows/restart-sharing.bat` (with `restart-sharing.ps1`) | Restarts Windows connection sharing for the Pi's cable (asks for admin) |
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
