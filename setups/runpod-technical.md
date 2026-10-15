# Runpod setup — technical

Current configuration for the `snngineV4_cloud` Runpod environment.
Rationale, alternatives, and open items: `runpod-rationale.md`.

## Infrastructure

- **Region**: `EU-RO-1` (all resources below live here).
- **Cloud Tier**: `SECURE` (enforced by network volume requirements; Community Cloud does not support volumes).
- **Network volume**: `qze81dpw7q` ("snngine-workspace"), 20GB Standard,
  `EU-RO-1`. Mount path on any pod: `/workspace`.
  Persistent layout:
  - `/workspace/venv`: Persistent Python 3.12 virtual environment (`--system-site-packages`).
  - `/workspace/wheels`: Persistent binary wheel cache (e.g. `pycuda-2026.1-cp312-cp312-linux_x86_64.whl`).
  - `/workspace/output`: Remote simulation video outputs managed under a 5-video rolling retention policy.
  - `/workspace/snngineV4_cloud`: Persistent repository checkout with compiled C++/CUDA backend (`.so`).
  - `/workspace/snngineV4_agent_branches`: Symlink pointing to `snngineV4_cloud/snngineV4_agent_branches`.
- **CPU pod**: none currently exists.
- **GPU pod**: none currently running (ephemeral). Validated GPU classes in `EU-RO-1`:
  - `NVIDIA RTX 4090` (24 GB VRAM, Ada)
  - `NVIDIA RTX PRO 4000 Blackwell` (24 GB VRAM, Blackwell)
  Pods are provisioned on demand and terminated immediately upon artifact delivery ($0.00/hr idle compute spend).
- **Base image**: `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404` (Ubuntu 24.04 LTS, Python 3.12, CUDA 12.8, PyTorch 2.8.0).
- **Tooling**:
  - Claude Code: `runpod` plugin (`runpod/runpod-plugins-official`), authenticated MCP connection.
  - Gemini CLI / Antigravity: official Runpod skills installed globally in `~/.gemini/config/skills/`, hosted Streamable HTTP MCP server registered in `~/.gemini/config/mcp_config.json` (`https://mcp.getrunpod.io/`).
  - Stock discovery: `setups/runpod_find_combos.py` (queries Runpod GraphQL API for live stock in `EU-RO-1` with zero third-party dependencies).
  - Pod execution & artifact download: `setups/runpod-engine-smoke-test/exec_pod.py` (Windows OpenSSH `-O` legacy SCP protocol, batch execution, artifact download).
  - Headless engine smoke test: `setups/runpod-engine-smoke-test/runpod_engine_test_runner.sh` and `test_headless_engine_sim.py` (progressive stages, compiler error pruning, timeout guards).
  - Headless video generation runner: `setups/runpod-engine-smoke-test/runpod_video_runner.sh` (environment activation, wheel caching, headless video generation, and rolling retention pruning).
  - Offscreen 3D video generator: `setups/runpod-engine-smoke-test/generate_simulation_video.py` (hardware-accelerated offscreen EGL VisPy 3D neural activity renderer and H.264 MP4 encoder).

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
- **Container Driver Capabilities**: Any custom container image or Docker execution requires:
  ```bash
  export NVIDIA_VISIBLE_DEVICES=all
  export NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics,display
  ```
  `graphics,display` is mandatory to inject NVIDIA userspace EGL and OpenGL driver libraries (`libEGL_nvidia.so.0`, `libglvnd`) into the container.
- **Runtime NVCC Availability**: PyCUDA `SourceModule` JIT compiles CUDA kernels at runtime by invoking `nvcc`. `/usr/local/cuda/bin` must be prepended to `PATH` in all non-interactive SSH and subshell invocations to prevent compilation failures.
- PyCUDA with OpenGL interop compiled from `main` (`pycuda-2026.1`) against CUDA with `CUDA_ENABLE_GL = True`, `CXXFLAGS = ['-I<numpy.get_include()>']`, and symlinked `numpy/_core/include` to resolve NumPy 2.x C-API restructuring. Cached as binary `.whl` in `/workspace/wheels/` and installed in `/workspace/venv`.
- C++/CUDA backend built via CMake in `snngine_v4/nn/cuda_backend/build/`.

## Headless Simulation & Video Rendering Verification

Verified in engine smoke test and video generation runs ([`setups/runpod-engine-smoke-test/runpod-engine-smoke-test-report.md`](runpod-engine-smoke-test/runpod-engine-smoke-test-report.md), [`setups/runpod-engine-smoke-test/runpod-engine-video-report.md`](runpod-engine-smoke-test/runpod-engine-video-report.md)):
- **Simulation Execution Rate**: 100 consecutive timesteps executed on an NVIDIA RTX 4090 at **0.121 ms/step** (~8,264 steps/sec) with membrane potentials bounded in physiological resting ranges ($[-70.12, -64.42] \text{ mV}$) and zero GUI/display dependencies.
- **Hardware-Accelerated Video Rendering & High-Resolution Scaling**:
  - **720p (H.264)**: 300 simulation steps (stride 2, 150 frames, 30 fps, $1280 \times 720$) rendered in 2.60s (**57.8 fps**, $> 1.9\times$ real-time, $0.75\text{ MB}$).
  - **1080p (H.264)**: 150 frames at $1920 \times 1080$ rendered in 4.76s (**31.5 fps**, $1.30\text{ MB}$) with orbital elevation easing.
  - **4K UHD (H.265 / HEVC)**: 150 frames at $3840 \times 2160$ rendered in 15.46s (**9.7 fps**, **$0.60\text{ MB}$**) with `libx265`. Demonstrates $> 50\%$ bitrate savings over 1080p H.264 at $4\times$ pixel density.
  - **Extended Duration & Focal Stimulation (1080p H.264)**: 1,200 simulation steps (stride 2, 600 frames, 20.0s @ 30 fps, $1920 \times 1080$) rendered in 36.82s (**16.3 fps**, $3.99\text{ MB}$) with targeted focal activation on 40/200 neurons (20% spatial cluster at $p_t = 0.35$). Produced 855 spikes with multi-stop dynamic colormap spanning resting ($-70\text{ mV}$ deep blue) through active firing (brilliant white flash).
- **Thalamic Stimulation & Distinct Subset Activation Contract**: Row 0 of `N_props` (`pt`, thalamic input probability) defaults to $0.0$ in `default_init`, leaving quiescent networks in resting equilibrium ($I=0$). Activating group flags (`L_Group_flags[1, :] = 1`) and assigning $p_t > 0$ to a localized spatial subset (`N_props[0, stim_indices] = 0.35`) produces clear contrast between active focal bursts and quiescent resting baseline.
- **Automatic System Package Verification on Boot**: While the persistent virtual environment and wheel cache reside on `/workspace`, container userspace packages are ephemeral. `runpod_video_runner.sh` implements an automated `ensure_system_packages` sentry checking `libEGL.so` to install required Mesa/EGL headers (`libegl1-mesa-dev`, `libgl1-mesa-dev`) via `apt-get` on fresh pod instances without manual intervention.
- **Plot Buffer Contract Dimensions**: Plot buffer configs use `.size_x` (e.g. `volt_plot.config.size_x` and `firings_scatter_plot.config.size_x`), not `.len`. Headless position VBO requires 14 floats per neuron initialized with spatial coordinates (`pos_vbo_mock[:, :3] = element.N_pos`).
- **TensorDataFrame C-Contiguity Requirement**: Backing tensors initialized from `pandas.DataFrame.values` inherit column-major stride `(1, N)`. C++/CUDA kernels (e.g. `fill_N_flags_group_id_and_G_neuron_count_per_type_`) calculate linear device offsets as `n + row * N`, which wraps strided writes into adjacent rows unless `.contiguous()` is enforced on GPU tensors.
- **Numpydantic Dynamic Identity Mapping**: Dynamic evaluation of `numpydantic.NDArray[Shape, Dtype]` produces distinct class instances (`id(dt1) != id(dt2)`), failing `ArrayInterfaces().dtype_interface_map.inv` lookups. The headless harness dynamically resolves interfaces by `(shape, dtype)` equivalence via `patch_array_interfaces()`.
- **Headless Chemical Diffusion Volume Mocking**: `Simulator._make_simulator_backend` unconditionally binds raw pointers for chemical diffusion volumes (`chemicals.C0` and `C1`). Headless execution without VisPy GLIR canvases maps `GLBufferTypes.TEXTURE_3D.name` to zero-initialized device tensors wrapped in `MockGLTensorDict` providing no-op `.copy_to_texture()` callbacks.
- **Linear VBO vs. Non-Linear 3D Texture Memory**: `GLBuffer.numba_device_array` requires linear device memory (`__cuda_memory__ = True`). 3D textures mapped via `RegisteredImage` produce non-linear CUDA `Array` instances that cannot be wrapped into Numba or PyTorch; they require explicit `Memcpy3D` copies (`copy_to_texture` / `copy_to_tensor`).
- **Network Volume Filesystem Permissions**: `/workspace` mounts an MFS network filesystem that rejects client `chown` calls (`Operation not permitted`). Tooling must omit owner and group preservation during file synchronization.
- **PyCUDA Source Import Shadowing**: Executing `python -c "import pycuda"` inside `/tmp/pycuda` attempts to import the source tree rather than the compiled site-package, failing with `ModuleNotFoundError: No module named 'pycuda._driver'`. Scripts must execute from `/root` or `/workspace`.
- **NumPy 2.x Read-Only Buffer Flags**: On Ubuntu 24.04 / Python 3.12 containers running NumPy 2.x, numpy views produced during host-device synchronization default to `flags.writeable = False`. In-place slice updates (`dest[:] = v.cpu().numpy()`) require checking and re-enabling write flags (`dest.setflags(write=True)`).
- **Windows OpenSSH 9.5 SCP Protocol**: OpenSSH 9.0+ defaults to SFTP. Connecting from Windows OpenSSH 9.5 against Runpod container `sshd` instances without active SFTP subsystems hangs indefinitely. Automation scripts must pass `-O` to force legacy SCP transport.

