# RunPod setup — rationale

Decisions, reasoning, alternatives rejected, and open items for the
`snngineV4_cloud` RunPod environment. Current configuration:
`runpod-technical.md`.

**Standing principle (2026-09-28): keep pieces modular/reusable rather
than one-off.** Applies wherever this work builds something with more
than one plausible reuse — the hardened image's entrypoint/capability-
drop logic, bridge-server tool additions, Pi-hosted services — favor a
separable, generic shape over something wired specifically to this one
deployment.

**2026-09-28 — Phone-triggered pod spin-up: extend the existing bridge
server (the sandbox project's own MCP), not ad hoc tool calls.** Spinning
up a RunPod pod from a phone session needs to be a one-command action
(volume ID, region, GPU, pod config are error-prone to recall each
time), not something solved by generic MCP tool calls in a Remote
Control session. Plan is to expand the bridge server, hosted on the Pi (not the
maintainer's dev machine) — otherwise the trigger path would inherit the
same host-dependency problem this whole RunPod effort exists to avoid.
Not yet designed or built; per this repo's rule against unprompted
custom scripts/workarounds, this needs its own explicit proposal before
any code is written, not something to start from this note alone.
Pi-side details: `pi-rationale.md`.

Started from a research-agent-generated blueprint
(`docs/research/runpod_setup.md` in the sandbox repo): a "decoupled"
architecture (persistent volume + cheap CPU pod + ephemeral GPU pod).
Treated as a starting point, not a spec — its prices and constraints
needed live verification against RunPod's actual API/catalog, and its
financial model and MCP-tooling choice needed correcting to fit intent.

## Decisions

**2026-09-27 — Region: `EU-RO-1`.** The blueprint's implicit assumption
— that a data center with GPU stock also supports network volumes — is
false in general. `EU-CZ-1` (RTX 3090 stock, `LOW`) and `EU-SE-1` (RTX
A40 stock, `LOW`) were the naive picks from GPU pricing alone; RunPod's
API rejects network-volume creation in `EU-CZ-1` outright (undocumented
anywhere, only surfaced by trying it), and `EU-SE-1` has no CPU-pod
stock at all. Cross-checking full GPU stock against the list of
data centers that actually support network volumes (`AP-JP-1`,
`CA-MTL-3`, `CA-MTL-4`, `EU-NL-1`, `EU-RO-1`, `EUR-IS-1`, `EUR-IS-3`,
`EUR-NO-1`, `US-CO-1`, `US-IL-1`, `US-MO-2`, `US-NC-2`, `US-NE-1`,
`US-TX-3`) found no overlap at all with any 24GB-class card
(3090/A40/A5000/A6000/4090) — only pricier cards (H100+, $3.49/hr+) or
smaller Ampere cards. `EU-RO-1` was the pivot: volume support, `HIGH`
CPU-pod stock across every flavor (best of any region checked), and live
stock of three cheap Ampere cards. Accepted trade-off: smaller VRAM
(16–20GB) than the original RTX 3090 target — acceptable because VRAM is
confirmed not a constraint for this workload. RTX A5000, the blueprint's
own recommended pick, turned out to have zero current stock anywhere
despite still listing a price — a live-catalog fact the blueprint had no
way to know.

**2026-09-27 — GPU: RTX 2000 Ada.** Cheapest of the three Ampere options
with live stock in `EU-RO-1` (A4500 $0.25/hr/20GB, RTX 4000 Ada
$0.28/hr/20GB were the alternatives, at $0.24/hr/16GB). Binary/VRAM
compatibility deferred to a smoke test rather than decided upfront.
Stock is `LOW`, not guaranteed — re-check before provisioning.
*(2026-10-15 update: subsequent validation runs used live in-stock Ada and Blackwell hardware: NVIDIA RTX PRO 4500 Blackwell for initial zero-copy interop, RTX 4090 for the headless engine simulation smoke test, and RTX PRO 4000 Blackwell for offscreen EGL video rendering; see `runpod-technical.md`).*

**2026-09-27 — Storage: 20GB Standard, no early resize.** $0.07/GB/month,
billed continuously with or without an attached/running pod — no pause
state exists, so tearing down and re-syncing to save money doesn't pay
off at this scale (~$0.046/day either way). A volume is pinned
permanently to its creation data center — confirmed against the
`update-network-volume` tool schema (only `name`/`size` are mutable, no
`dataCenter` field) — so moving means creating a new volume elsewhere and
copying data via two simultaneously-running pods (`runpodctl send/
receive` or `rsync` over SSH). Scriptable, cheap in raw compute, manual/
fiddly; deferred until actually needed.

**2026-09-27 — Financial model: fixed recurring cost, GPU manual-only.**
Volume + CPU pod are the steady cost. The GPU pod is launched only on
explicit user decision, never autonomously by an agent — rejects the
blueprint's "Routine B", which assumed the agent would launch/terminate
GPU pods on its own.

**2026-09-27 — Tooling: the official `runpod` Claude Code plugin.**
Rejects the blueprint's proposed `npx -y @runpod/mcp-server@latest` with
a bare `RUNPOD_API_KEY` on disk — unsandboxed, no scoping. The plugin
(marketplace `runpod/runpod-plugins-official`) gives an authenticated
MCP connection plus its own skills instead.

**2026-09-28 — Threat model: full agent containment, not rented-VM
hygiene.** This pod runs an LLM-driven agent with tool access,
potentially prompt-injected — the same threat model this sandbox repo's
local Docker setup exists to address, not ordinary VM security.

**2026-09-28 — RunPod's own API key never enters any pod.** Stays at the
orchestration layer (the host session's plugin connection). Already true
by construction; nothing to build.

**2026-09-28 — Agent operating credentials go through RunPod
`create-secret`, not raw pod `env`.** Values are write-only, never
readable back through the API, substituted into a pod's env only at
boot (`{{ RUNPOD_SECRET_<name> }}`). This protects a key from RunPod's
own API/account layer only — it does not protect it from anything with
shell access inside the pod once substituted, which is a separate
problem (see containment decisions below), not one this mechanism
solves. Actual key list still undecided.

**2026-09-28 — Filesystem/process containment: self-dropping root
entrypoint, not a launcher flag.** `create-pod` has no equivalent to
`docker run`'s `--user`/`cap_drop`/`security_opt`. Plan: a root-starting
custom-image entrypoint that calls `prctl(PR_CAPBSET_DROP)` (possible
because root holds `CAP_SETPCAP`) and sets `no-new-privileges` on itself,
then hands off to a non-root user — the same voluntary-self-restriction
approach `guard-exec` already uses for Landlock, extended to
capabilities. Accepted trade-off: a brief window where the entrypoint
runs as root before dropping, versus a launcher-enforced `--cap-drop`
having zero extra capabilities from the first instruction. Read-only
rootfs was checked against this repo's own `docker-compose.yml` and
found to only apply to the `egress-proxy` sidecar, not the main
`agent-sandbox` container — so it isn't a missing protection to
replicate here at all.

**2026-09-28 — Egress: dedicated always-on separate machine, no weaker
fallback mode, ever.** The local sandbox's `egress-proxy` is the sole
exit point for the agent *and* all three MCP servers (`web-fetch`,
`github-mcp`, `repo-loader` are all `internal`-only in Docker terms,
routed via `HTTPS_PROXY`) — that isolation comes from Docker network
topology, which has no equivalent inside one RunPod pod. Same-pod Squid
+ Landlock alone was rejected as strictly weaker (Landlock forces
traffic through one point, proven working — see Evidence — but can't
protect the proxy process from the agent process in a shared namespace);
a second RunPod pod over public ports was rejected on cost/auth
complexity; routing through the maintainer's own dev host was rejected
outright as defeating the point of using RunPod at all. Decided instead:
a dedicated always-on separate machine, reached over Tailscale. Full
comparison and the machine's own setup: `pi-rationale.md`.

**2026-09-28 — RunPod-native alternatives checked, not adopted.**
`companion-clis`' GitHub integration is the raw `gh` CLI with a real
unscoped token on disk — a downgrade from `github-mcp`, not a
replacement. RunPod Serverless (genuinely separate compute, no shared
network namespace) could host the three MCP servers with real isolation,
but its request/response job model doesn't map cleanly onto MCP's
persistent-session shape and cold starts can run minutes — not pursued
further, undecided.

**2026-09-28 — Porting the whole local `docker-compose` stack into one
RunPod pod: ruled out.** Would have recreated the `internal`/`egress`
network split natively via nested Docker. Live-tested and failed — see
Evidence.

## Evidence

**Landlock works inside a RunPod pod (2026-09-27).** Tested directly by
SSHing into a `ubuntu:24.04` CPU pod (host kernel `6.8.0-85-generic`) and
running the real syscalls `guard-exec` uses: `landlock_create_ruleset`
returned ABI 4 (meets `guard-exec`'s own floor for network rules; lower
than this repo's own local containers' ABI 8, but nothing `guard-exec`
uses needs more than 4 — it deliberately omits ABI 6+'s `IOCTL_DEV`
already). `prctl(PR_SET_NO_NEW_PRIVS)` succeeded. A ruleset granting only
`/tmp`, followed by `landlock_restrict_self`, then tested directly:
`/tmp` opened fine, `/etc` was denied with `Permission denied` — real
kernel-enforced denial, not just non-error syscalls.

**Docker-in-Docker fails inside a RunPod pod (2026-09-27).** Installed
`docker.io` in a CPU pod and ran `dockerd` directly as root:
```
failed to register "bridge" driver: failed to create NAT chain DOCKER:
iptables --wait -t nat -N DOCKER: iptables v1.8.10 (nf_tables):
Could not fetch rule set generation id: Permission denied (you must be root)
```
`dockerd` itself starts; its bridge driver cannot create its NAT chain —
no netfilter/nftables access from inside the pod, even as root. This is
the exact machinery the local `internal`/`egress` split depends on, so
it rules out any nested multi-network compose topology on RunPod, not
Docker specifically.

**Stopped pods can fail to restart (2026-09-27).** Hit `"There are not
enough free memory on the host machine to start this pod"` restarting a
stopped pod. A stopped pod is tied to its specific physical host; if
that host fills up, it cannot restart there. Contradicts the blueprint's
claim that RunPod "eliminates host re-rent risks" relative to Vast.ai —
that specific claim does not hold as stated. Worked around by
terminating and creating a fresh pod instead of restarting the stuck
one.

**RunPod's SSH proxy is interactive-only (2026-09-27).**
`ssh.runpod.io` ignores a command passed as an SSH argument and always
opens a login shell; needs `-tt`; garbled a single very long (16KB) line
sent via stdin (short multi-line stdin works fine); no `scp`/`sftp`
support at all ("subsystem request failed"). Direct SSH (exposing
`22/tcp` on the pod, real `sshd`) is needed for anything beyond quick
interactive checks.

**2026-10-15 — Persistent network volume environment & wheel caching (`/workspace/venv`, `/workspace/wheels/`).**
Ephemeral GPU pods boot from a clean container image. Re-running `apt-get`, downloading packages, and compiling PyCUDA from source on every spin-up wasted 5–10 minutes and incurred billable compute charges. To eliminate this overhead, all Python dependencies and pre-compiled wheels are persisted on volume `qze81dpw7q`:
- `/workspace/venv`: Pre-populated virtual environment with `--system-site-packages`, containing `torch`, `vispy`, `imageio`, `numpydantic`, and dependencies.
- `/workspace/wheels/`: Cached binary `.whl` files (specifically `pycuda-2026.1-cp312-cp312-linux_x86_64.whl`).
Fresh pods activate `/workspace/venv` directly or install the cached wheel in $< 3\text{ seconds}$ without network downloads or recompilation.

**2026-10-15 — Preservation of PyCUDA native OpenGL interop (`pycuda.gl`).**
Mocking or bypassing PyCUDA was explicitly rejected. `snngine_v4` relies on PyCUDA's OpenGL interop (`pycuda.gl.RegisteredBuffer` and `pycuda.gl.RegisteredImage`) to bind device memory directly to VisPy visual buffers without host roundtrips. PyCUDA must be natively compiled with `CUDA_ENABLE_GL = True` and operational on the GPU device to ensure true interop validation.

**2026-10-15 — PyCUDA NumPy 2.x C-API compatibility & include bridging.**
PyCUDA `v2024.1` fails to build against NumPy 2.x due to removed C-API members (`PyArray_Descr.elsize`, `PyArray_CORDER`). The `main` branch (`pycuda-2026.1`) provides native NumPy 2.x compatibility. Furthermore, NumPy 2.x moved internal headers to `numpy/_core/include`; PyCUDA's build requires explicit `CXXFLAGS = ['-I<numpy.get_include()>']` and a symlink from `numpy/_core/include` to `numpy/core/include` during compilation.

**2026-10-15 — Rolling video retention policy on persistent volume.**
Storage on volume `qze81dpw7q` is capped at 20 GB. Storing unmanaged simulation recordings would risk storage exhaustion, breaking future pod boots and builds. An automated rolling window policy was implemented in `runpod_video_runner.sh`:
- Retains a maximum of 5 recent simulation video runs (`simulation_*.mp4` and companion `.json`) on `/workspace/output/`.
- Dynamically throttles retention to 2 videos if free space $< 2\text{ GB}$, and 1 video if $< 1\text{ GB}$.
- Purges oldest runs in FIFO order following successful artifact generation.

**2026-10-15 — Windows OpenSSH 9.5 legacy SCP flag (`-O`).**
OpenSSH 9.0+ transitioned the default `scp` transfer protocol from legacy RCP/SCP to SFTP. On Windows clients connecting to Runpod container `sshd` instances that lack an active SFTP subsystem, file transfers hang indefinitely until socket timeout. Passing the `-O` flag forces the legacy SCP protocol, restoring fast, non-blocking transfer for automation scripts.

**2026-10-15 — Headless H.264 video rendering vs. real-time WAN WebSocket streaming.**
In `runpod-smoke-tests/runpod-smoke-test-report.md`, real-time interactive streaming of raw 800×600 RGBA frame buffers over WebSockets consumed ~460 Mbps (57.6 MB/s) of continuous uplink from `EU-RO-1` across Cloudflare, inducing significant TCP window buffer bloat and visual stuttering. For automated neural simulation telemetry and inspection, local containerized H.264/MP4 encoding via offscreen EGL VisPy rendering was selected instead:
- Eliminates WAN bandwidth sensitivity entirely; rendering runs at hardware speed (57.8 fps, > 1.9x real-time).
- Produces compact, self-contained media artifacts (~0.75 MB for 5 seconds of 720p at 30 fps).
- Preserves frame-accurate temporal synchronization between spatial neuron state flashes and camera orbits.

**2026-10-15 — Storage filesystem permissions on network volume (`mfs`).**
Runpod's network volumes (`mfs#euro-3.runpod.net`) reject POSIX user/group ownership mutations by container clients (`chown` operations fail with `Operation not permitted (1)`). Synchronization scripts and tooling (`exec_pod.py`, `rsync`) must strictly omit owner/group preservation flags (`--no-owner --no-group`) to prevent transfer aborts.

**2026-10-15 — Memory layout contiguity in host-device tensor transfers.**
`TensorDataFrame` backing tensors constructed from pandas DataFrame objects inherit column-major (Fortran) memory ordering with stride `(1, N_rows)`. Because the native C++/CUDA simulation kernels (`snn_simulation_gpu`, `snn_construction_gpu`) calculate linear memory offsets assuming standard C-contiguous (row-major) layout (`offset = n + row * N`), passing uncorrected strided pointers causes Row 2 (`L_group`) writes to wrap across row boundaries into Row 1 (`N_type`), corrupting neuron classification flags. Enforcing `gpu_t = gpu_t.contiguous()` during tensor construction is a mandatory invariant for all cloud GPU execution.

## Open items

Ordered by dependency, not just file order. Item 0 is a gate, not just
first-in-sequence: if it surfaces a real incompatibility, everything
below pauses until resolved.

0. **RESOLVED 2026-10-15 — Gate: dependency validation & C++/CUDA compilation.**
   Confirmed on live Runpod GPU hardware in `EU-RO-1` (tested on RTX 4090 and RTX PRO 4000 Blackwell): CUDA 12.8 / 13.0, PyTorch 2.8.0, native PyCUDA 2026.1 with OpenGL interop, and the C++/CUDA simulation backend (`snngine_v4/nn/cuda_backend/build/`) compile and execute cleanly without numerical drift or NaN faults. Headless 3D offscreen EGL video rendering benchmarked at 57.8 frames/sec.
1. Design + build the custom hardened pod image (root-starting
   entrypoint: capability drop, `no-new-privileges`, drop to non-root;
   `guard-exec` wired in; real toolchain from item 0 baked in).
2. Decide the agent credential list (LLM auth, git, etc.); wire via
   RunPod `create-secret`. Blocks nothing else in this list, but needed
   before a real agent session runs.
3. Run the Phase 1 bootstrap on a real CPU pod using the image from
   item 1; verify persistence across stop/restart.
4. Re-check `EU-RO-1` GPU stock immediately before provisioning the GPU
   pod.

Standalone, not blocking anything above:
- Compare against Vast.ai given how tight RunPod's real Ampere stock is
  — raised, not yet done.
- RunPod Serverless as an MCP-server host: not pursued past the initial
  "shape doesn't fit cleanly" observation.
- **RESOLVED 2026-09-28 — admin/jump pod for Pi login access: not
  needed.** Raised the same day as a candidate (a separate throwaway
  RunPod pod + dedicated volume, isolated from the CPU/GPU agent pods,
  for completing `claude /login` on a future Pi-hosted Claude Code
  instance — "host-pi-claude", see `pi-rationale.md` item 3 — without
  folding that privileged action into the agent's own untrusted
  execution environment). Superseded by **Tailscale SSH Console**: a
  browser-based SSH session built into the Tailscale admin console
  itself (WebAssembly — Tailscale client, WireGuard, and an SSH client
  all run in the browser tab, which becomes an ephemeral tailnet node
  for the session's duration only). No RunPod pod, no volume, no client
  software of any kind — just a browser and the tailnet owner's login,
  from any device, including a phone. Verified against Tailscale's own
  docs (`tailscale.com/docs/features/tailscale-ssh/tailscale-ssh-console`),
  currently in beta. Requires two things on the Pi side once it's set
  up: **Tailscale SSH enabled** (`tailscale up --ssh`, not just plain
  Tailscale networking) and **a Tailscale ACL policy rule** permitting
  SSH access to that node on port 22 — both still to do once the Pi is
  actually on the tailnet (`pi-rationale.md` item 5).

Pi-side items (host setup, bridge-server expansion design): tracked in
`pi-rationale.md`, not duplicated here.
