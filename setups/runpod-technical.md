# Runpod setup — technical

Current configuration for the `snngineV4_cloud` Runpod environment.
Rationale, alternatives, and open items: `runpod-rationale.md`.

## Infrastructure

- **Region**: `EU-RO-1` (all resources below live here).
- **Cloud Tier**: `SECURE` (enforced by network volume requirements; Community Cloud does not support volumes).
- **Network volume**: `qze81dpw7q` ("snngine-workspace"), 20GB Standard,
  `EU-RO-1`. Mount path on any pod: `/workspace`.
- **CPU pod**: none currently exists.
- **GPU pod**: none currently exists. Target when created: RTX 2000 Ada (or available Ada/Ampere equivalent),
  `EU-RO-1`.
- **Base image**: `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404` (Ubuntu 24.04 LTS, Python 3.12, CUDA 12.8, PyTorch 2.8.0).
- **Tooling**:
  - Claude Code: `runpod` plugin (`runpod/runpod-plugins-official`), authenticated MCP connection.
  - Gemini CLI / Antigravity: official Runpod skills installed globally in `~/.gemini/config/skills/`, hosted Streamable HTTP MCP server registered in `~/.gemini/config/mcp_config.json` (`https://mcp.getrunpod.io/`).
  - Stock discovery: `setups/runpod_find_combos.py` (queries Runpod GraphQL API for live stock in `EU-RO-1` with zero third-party dependencies).
  - Headless engine smoke test: `setups/runpod-engine-smoke-test/runpod_engine_test_runner.sh` and `test_headless_engine_sim.py` (progressive stages, compiler error pruning, timeout guards).

## Credentials

- Runpod API key: held by the orchestrating host session (in `setups/.secrets/.env` as `RUNPOD_API_KEY`). Never passed into any pod or printed to stdout.
- Agent operating credentials (LLM auth, git, etc.): not yet enumerated.
  Mechanism when they are: Runpod `create-secret`, referenced from a
  pod's `env` as `{{ RUNPOD_SECRET_<name> }}`.

## Security / containment

Not yet built:
- Custom hardened pod image: root-starting entrypoint that self-drops
  capabilities (`prctl(PR_CAPBSET_DROP)`) and sets `no-new-privileges`,
  then hands off to a non-root user; `guard-exec` copied in and wired up
  for the agent's shell-tool calls (filesystem + network-port Landlock
  restriction).
- Egress proxy host: a dedicated always-on machine (a PoE Raspberry Pi)
  running `egress-proxy`, reached from the Runpod pod over Tailscale.
  Not yet set up; dedicated-vs-shared-instance not yet decided.

## Bootstrap

Verified in prior smoke test ([`setups/runpod-smoke-tests/runpod-smoke-test-report.md`](runpod-smoke-tests/runpod-smoke-test-report.md)):
- Mesa/EGL headers: `libgl1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev libglvnd-dev`.
- Environment exports:
  ```bash
  export PATH="/usr/local/cuda/bin:${PATH:-}"
  export LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}"
  export PYOPENGL_PLATFORM="egl"
  ```
- PyCUDA with OpenGL interop compiled from source against CUDA 12.8 with `--cuda-enable-gl`.
- C++/CUDA backend built via CMake in `snngine_v4/nn/cuda_backend/`.
