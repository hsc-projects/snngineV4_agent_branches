"""
Phase 4 Smoke Test: Containerized Interactive Web Bridge for Zero-Copy CUDA-OpenGL Interoperability.

Architectural Purpose:
  Runs the complete 5-link zero-copy interop pipeline inside a headless Docker container (or remote RunPod pod)
  without requiring a physical monitor or host X11 display socket.
  
  Rendering:
    Uses VisPy with native NVIDIA EGL (vispy.use('egl')) directly bound to /usr/lib/x86_64-linux-gnu/libEGL_nvidia.so.0.
    Bypasses X11, Xvfb, VirtualGL, and Mesa software rasterization entirely, enabling full NVIDIA hardware
    acceleration and genuine pycuda.gl.RegisteredBuffer VBO mapping.

  Interactive Streaming Bridge:
    Embedded pure Python standard library HTTP & RFC 6455 WebSocket server on port 6080.
    Streams raw hardware-rendered RGBA frames at 30 FPS directly to an HTML5 Canvas (putImageData).
    Receives interactive client commands (mouse orbit, zoom, pause/resume, single-step, kernel toggle)
    and dynamically applies them to VisPy's TurntableCamera and CUDA simulation pipeline.

5-Link Interop Chain:
  Link 1: Hand-written CUDA simulation code (update_N_state_kernel from sister repo sim_demo_utils).
  Link 2: PyCUDA built with OpenGL interoperability (pycuda.gl).
  Link 3: PyCUDA RegisteredBuffer mapped directly from VisPy's OpenGL VBO.
  Link 4: Mapped device pointer wrapped as a numba.cuda.cudadrv.devicearray.DeviceNDArray.
  Link 5: PyTorch tensor view wrapping the Numba device array (torch.as_tensor).

Usage:
  Local Container:
    setups/gpu-smoke-test/interop_smoke_test_docker_launcher.sh --web
    Browser: http://localhost:6080

  RunPod Cloud Pod:
    ./runpod_smoke_runner.sh --web
    Browser: https://<pod-id>-6080.proxy.runpod.net (or pod public IP:6080)
"""

import argparse
import asyncio
import base64
import ctypes
import hashlib
import json
import os
import struct
import sys
import time
import types
from pathlib import Path

# Force EGL platform before any OpenGL / VisPy imports
os.environ['PYOPENGL_PLATFORM'] = 'egl'

import numpy as np

# Ensure project root and sister repo are in sys.path
parents = Path(__file__).resolve().parents
PROJECT_ROOT = parents[2] if len(parents) > 2 else parents[0]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Setup dummy IPython / pandas modules in case sim_demo_utils requires them
if 'IPython' not in sys.modules:
    ipython = types.ModuleType('IPython')
    ipython_display = types.ModuleType('IPython.display')
    ipython_display.display_html = lambda *a, **k: None
    ipython.display = ipython_display
    sys.modules['IPython'] = ipython
    sys.modules['IPython.display'] = ipython_display

if 'pandas' not in sys.modules:
    pandas = types.ModuleType('pandas')
    pandas.DataFrame = lambda *a, **k: None
    sys.modules['pandas'] = pandas


# RFC 6455 WebSocket Protocol Constants & Helpers
MAGIC_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def compute_accept_key(sec_key: str) -> str:
    """Compute RFC 6455 Sec-WebSocket-Accept handshake header."""
    sha = hashlib.sha1((sec_key.strip() + MAGIC_GUID).encode('utf-8')).digest()
    return base64.b64encode(sha).decode('ascii')


def make_frame(payload: bytes, opcode: int = 0x2) -> bytes:
    """Pack payload into an RFC 6455 WebSocket frame (server to client, unmasked)."""
    length = len(payload)
    header = bytearray()
    header.append(0x80 | (opcode & 0x0F))  # FIN=1, Opcode
    if length < 126:
        header.append(length)
    elif length <= 0xFFFF:
        header.append(126)
        header.extend(struct.pack('>H', length))
    else:
        header.append(127)
        header.extend(struct.pack('>Q', length))
    return bytes(header) + payload


def parse_client_frame(data: bytearray):
    """Parse incoming RFC 6455 frame from client (must be masked)."""
    if len(data) < 2:
        return None
    b0 = data[0]
    b1 = data[1]
    opcode = b0 & 0x0F
    is_masked = bool(b1 & 0x80)
    payload_len = b1 & 0x7F
    offset = 2

    if payload_len == 126:
        if len(data) < 4:
            return None
        payload_len = struct.unpack('>H', data[2:4])[0]
        offset = 4
    elif payload_len == 127:
        if len(data) < 10:
            return None
        payload_len = struct.unpack('>Q', data[2:10])[0]
        offset = 10

    mask = None
    if is_masked:
        if len(data) < offset + 4:
            return None
        mask = data[offset:offset + 4]
        offset += 4

    if len(data) < offset + payload_len:
        return None

    raw_payload = data[offset:offset + payload_len]
    if is_masked and mask:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(raw_payload))
    else:
        payload = bytes(raw_payload)

    total_consumed = offset + payload_len
    return opcode, payload, total_consumed


class ExternalMemory:
    """External GPU memory wrapper conforming to Numba CUDA device array requirements."""
    __cuda_memory__ = True

    def __init__(self, ptr: int, size: int):
        self.device_ctypes_pointer = ctypes.c_void_p(ptr)
        self._cuda_memsize_ = size


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SNNgineV4 — CUDA-OpenGL Zero-Copy Web Bridge</title>
  <style>
    :root {
      --bg-primary: #0e1117;
      --bg-secondary: #161b22;
      --bg-card: #21262d;
      --border-color: #30363d;
      --accent-cyan: #58a6ff;
      --accent-green: #3fb950;
      --accent-orange: #d29922;
      --accent-red: #f85149;
      --accent-purple: #bc8cff;
      --text-main: #f0f6fc;
      --text-muted: #8b949e;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-primary);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px;
    }
    header {
      width: 100%;
      max-width: 1100px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      margin-bottom: 16px;
    }
    .header-title {
      font-size: 1.15rem;
      font-weight: 600;
      letter-spacing: 0.5px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
    }
    .badge-online { background: rgba(63, 185, 80, 0.2); color: var(--accent-green); border: 1px solid var(--accent-green); }
    .badge-connecting { background: rgba(210, 153, 34, 0.2); color: var(--accent-orange); border: 1px solid var(--accent-orange); }
    .badge-offline { background: rgba(248, 81, 73, 0.2); color: var(--accent-red); border: 1px solid var(--accent-red); }
    .badge-mode { background: rgba(88, 166, 255, 0.2); color: var(--accent-cyan); border: 1px solid var(--accent-cyan); }
    
    .stats-bar {
      width: 100%;
      max-width: 1100px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }
    .stat-card {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 10px 14px;
    }
    .stat-label {
      font-size: 0.72rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }
    .stat-val {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.95rem;
      font-weight: 600;
      color: var(--text-main);
    }
    
    .viewport-container {
      width: 100%;
      max-width: 1100px;
      position: relative;
      background: #000000;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      justify-content: center;
      align-items: center;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    }
    canvas#viewport {
      display: block;
      cursor: grab;
      width: 100%;
      max-width: 800px;
      height: auto;
      aspect-ratio: 4 / 3;
    }
    canvas#viewport:active {
      cursor: grabbing;
    }
    .viewport-overlay {
      position: absolute;
      top: 10px;
      left: 10px;
      background: rgba(14, 17, 23, 0.75);
      backdrop-filter: blur(4px);
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 0.75rem;
      color: var(--text-muted);
      pointer-events: none;
      font-family: monospace;
    }
    
    .controls-bar {
      width: 100%;
      max-width: 1100px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
      padding: 12px 16px;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      align-items: center;
    }
    button {
      background: var(--bg-card);
      color: var(--text-main);
      border: 1px solid var(--border-color);
      padding: 8px 14px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s, transform 0.05s;
    }
    button:hover {
      background: #30363d;
      border-color: #8b949e;
    }
    button:active {
      transform: scale(0.98);
    }
    button.btn-primary {
      background: #238636;
      border-color: #2ea043;
    }
    button.btn-primary:hover {
      background: #2ea043;
    }
    button.btn-warning {
      background: #9e6a03;
      border-color: #bb8009;
    }
    button.btn-warning:hover {
      background: #bb8009;
    }
    
    .instructions-panel {
      width: 100%;
      max-width: 1100px;
      margin-top: 16px;
      padding: 14px 18px;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      font-size: 0.82rem;
      color: var(--text-muted);
      line-height: 1.5;
    }
    .instructions-panel strong {
      color: var(--text-main);
    }
    .interop-links {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 8px;
      margin-top: 10px;
    }
    .link-tag {
      padding: 4px 8px;
      background: var(--bg-card);
      border-radius: 4px;
      font-family: monospace;
      font-size: 0.75rem;
      border-left: 3px solid var(--accent-cyan);
    }
  </style>
</head>
<body>

  <header>
    <div class="header-title">
      <span>SNNgineV4 — Zero-Copy Web Bridge</span>
      <span id="badgeConn" class="badge badge-connecting">Connecting...</span>
    </div>
    <div>
      <span id="badgeMode" class="badge badge-mode">CUDA Kernel</span>
      <span id="badgeState" class="badge badge-online">Running</span>
    </div>
  </header>

  <div class="stats-bar">
    <div class="stat-card">
      <div class="stat-label">Step / Sim Time</div>
      <div class="stat-val" id="valSteps">0000 (0.00s)</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Frame Rate (FPS)</div>
      <div class="stat-val" id="valFps">0.0 FPS</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Render Latency</div>
      <div class="stat-val" id="valRenderTime">0.0 ms</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">OpenGL VBO ID</div>
      <div class="stat-val" id="valVboId">#--</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Mapped VRAM Pointer</div>
      <div class="stat-val" id="valVramPtr">0x000000000000</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Neuron Firing Rate</div>
      <div class="stat-val" id="valFiring">0 / 64 active</div>
    </div>
  </div>

  <div class="viewport-container">
    <canvas id="viewport" width="800" height="600"></canvas>
    <div class="viewport-overlay" id="camOverlay">
      Camera: Azim 45.0° | Elev 25.0° | Dist 35.0
    </div>
  </div>

  <div class="controls-bar">
    <button id="btnToggleSim" class="btn-warning">Pause Simulation</button>
    <button id="btnStep">Step (1 Frame)</button>
    <button id="btnToggleMode">Switch to PyTorch Fallback</button>
    <button id="btnResetCam">Reset Camera</button>
    <span style="flex-grow: 1;"></span>
    <span style="font-size: 0.78rem; color: var(--text-muted);">
      🎮 Drag: Orbit | Scroll: Zoom | Double-click: Reset View
    </span>
  </div>

  <div class="instructions-panel">
    <strong>Zero-Copy Interoperability Verification:</strong>
    Direct hardware-rendered EGL offscreen framebuffer with zero CPU-GPU copy roundtrips.
    Mutations occur entirely in VRAM:
    <div class="interop-links">
      <div class="link-tag">Link 1: update_N_state</div>
      <div class="link-tag">Link 2: pycuda.gl</div>
      <div class="link-tag">Link 3: RegisteredBuffer</div>
      <div class="link-tag">Link 4: DeviceNDArray</div>
      <div class="link-tag">Link 5: torch.as_tensor</div>
    </div>
  </div>

  <script>
    const canvas = document.getElementById('viewport');
    const ctx = canvas.getContext('2d');
    let imgData = ctx.createImageData(canvas.width, canvas.height);

    const badgeConn = document.getElementById('badgeConn');
    const badgeMode = document.getElementById('badgeMode');
    const badgeState = document.getElementById('badgeState');
    const valSteps = document.getElementById('valSteps');
    const valFps = document.getElementById('valFps');
    const valRenderTime = document.getElementById('valRenderTime');
    const valVboId = document.getElementById('valVboId');
    const valVramPtr = document.getElementById('valVramPtr');
    const valFiring = document.getElementById('valFiring');
    const camOverlay = document.getElementById('camOverlay');

    const btnToggleSim = document.getElementById('btnToggleSim');
    const btnStep = document.getElementById('btnStep');
    const btnToggleMode = document.getElementById('btnToggleMode');
    const btnResetCam = document.getElementById('btnResetCam');

    let ws = null;
    let isPaused = false;
    let useCuda = true;
    let clientFrameCount = 0;
    let lastFpsTime = performance.now();
    let measuredClientFps = 0;

    function connectWs() {
      const proto = location.protocol === 'https:' ? 'wss://' : 'ws://';
      const wsUrl = proto + location.host + '/ws';
      badgeConn.className = 'badge badge-connecting';
      badgeConn.textContent = 'Connecting...';

      ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        badgeConn.className = 'badge badge-online';
        badgeConn.textContent = 'Connected';
      };

      ws.onmessage = (event) => {
        if (typeof event.data === 'string') {
          try {
            const data = JSON.parse(event.data);
            handleStatusUpdate(data);
          } catch (e) {
            console.error('JSON parse error:', e);
          }
        } else {
          // Binary RGBA frame data
          const raw = new Uint8ClampedArray(event.data);
          if (imgData.data.length === raw.length) {
            imgData.data.set(raw);
            ctx.putImageData(imgData, 0, 0);
          } else {
            // Dimension mismatch, recreate buffer
            const newImg = new ImageData(raw, canvas.width, canvas.height);
            ctx.putImageData(newImg, 0, 0);
          }
          clientFrameCount++;
          const now = performance.now();
          if (now - lastFpsTime >= 1000) {
            measuredClientFps = (clientFrameCount * 1000 / (now - lastFpsTime)).toFixed(1);
            clientFrameCount = 0;
            lastFpsTime = now;
          }
        }
      };

      ws.onclose = () => {
        badgeConn.className = 'badge badge-offline';
        badgeConn.textContent = 'Disconnected';
        setTimeout(connectWs, 2000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    function handleStatusUpdate(data) {
      if (data.type === 'init') {
        if (data.width && data.height) {
          canvas.width = data.width;
          canvas.height = data.height;
          imgData = ctx.createImageData(data.width, data.height);
        }
        return;
      }

      valSteps.textContent = `${String(data.step).padStart(4, '0')} (${data.sim_time}s)`;
      valFps.textContent = `${data.fps} srv / ${measuredClientFps} cli`;
      valRenderTime.textContent = `${data.render_time_ms} ms`;
      valVboId.textContent = `#${data.vbo_id}`;
      valVramPtr.textContent = data.vram_ptr;
      valFiring.textContent = `${data.fired_count} / ${data.n_markers} active`;

      isPaused = data.paused;
      if (isPaused) {
        badgeState.className = 'badge badge-connecting';
        badgeState.textContent = 'Paused';
        btnToggleSim.textContent = 'Resume Simulation';
        btnToggleSim.className = 'btn-primary';
      } else {
        badgeState.className = 'badge badge-online';
        badgeState.textContent = 'Running';
        btnToggleSim.textContent = 'Pause Simulation';
        btnToggleSim.className = 'btn-warning';
      }

      useCuda = data.use_cuda_kernel;
      if (useCuda) {
        badgeMode.className = 'badge badge-mode';
        badgeMode.textContent = 'CUDA Kernel';
        btnToggleMode.textContent = 'Switch to PyTorch Fallback';
      } else {
        badgeMode.className = 'badge';
        badgeMode.style.background = 'rgba(188, 140, 255, 0.2)';
        badgeMode.style.color = 'var(--accent-purple)';
        badgeMode.style.border = '1px solid var(--accent-purple)';
        badgeMode.textContent = 'PyTorch Fallback';
        btnToggleMode.textContent = 'Switch to CUDA Kernel';
      }

      if (data.camera) {
        camOverlay.textContent = `Camera: Azim ${data.camera.azimuth}° | Elev ${data.camera.elevation}° | Dist ${data.camera.distance}`;
      }
    }

    function sendAction(actionObj) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(actionObj));
      }
    }

    // Button event listeners
    btnToggleSim.addEventListener('click', () => {
      sendAction({ action: 'toggle_sim' });
    });

    btnStep.addEventListener('click', () => {
      sendAction({ action: 'step' });
    });

    btnToggleMode.addEventListener('click', () => {
      sendAction({ action: 'toggle_mode' });
    });

    btnResetCam.addEventListener('click', () => {
      sendAction({ action: 'reset_cam' });
    });

    // Mouse interactive camera handlers
    let isDragging = false;
    let lastX = 0, lastY = 0;

    canvas.addEventListener('mousedown', (e) => {
      isDragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
    });

    window.addEventListener('mouseup', () => {
      isDragging = false;
    });

    canvas.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      lastX = e.clientX;
      lastY = e.clientY;

      sendAction({
        action: 'orbit',
        dx: -dx * 0.4,
        dy: -dy * 0.4
      });
    });

    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const factor = e.deltaY > 0 ? 1.08 : 0.92;
      sendAction({
        action: 'zoom',
        factor: factor
      });
    }, { passive: false });

    canvas.addEventListener('dblclick', () => {
      sendAction({ action: 'reset_cam' });
    });

    // Touch support for mobile/tablet browsers
    let touchDist = 0;
    canvas.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        isDragging = true;
        lastX = e.touches[0].clientX;
        lastY = e.touches[0].clientY;
      } else if (e.touches.length === 2) {
        isDragging = false;
        touchDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
      }
    }, { passive: true });

    canvas.addEventListener('touchmove', (e) => {
      if (e.touches.length === 1 && isDragging) {
        const dx = e.touches[0].clientX - lastX;
        const dy = e.touches[0].clientY - lastY;
        lastX = e.touches[0].clientX;
        lastY = e.touches[0].clientY;
        sendAction({ action: 'orbit', dx: -dx * 0.4, dy: -dy * 0.4 });
      } else if (e.touches.length === 2) {
        const dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        if (touchDist > 0) {
          const factor = touchDist / dist;
          sendAction({ action: 'zoom', factor: factor });
        }
        touchDist = dist;
      }
    }, { passive: true });

    canvas.addEventListener('touchend', () => {
      isDragging = false;
      touchDist = 0;
    });

    // Start WebSocket connection
    connectWs();
  </script>
</body>
</html>
"""


class WebInteropServer:
    """
    Native EGL-backed 3D simulation and WebSocket server.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 6080, width: int = 800, height: int = 600,
                 fps: int = 30, n_markers: int = 64, timeout: float = None):
        self.host = host
        self.port = port
        self.width = width
        self.height = height
        self.target_fps = fps
        self.n_markers = n_markers
        self.timeout = timeout

        self.running = True
        self.total_steps = 0
        self.sim_time = 0.0
        self.use_cuda_kernel = True
        self.cuda_kernel_available = False

        self.canvas = None
        self.view = None
        self.camera = None
        self.markers = None
        self.vbo_id = None
        self.raw_ptr = None
        self.reg_buffer = None
        self.gl_tensor = None
        self.cu_ctx = None

        self.clients = set()
        self.step_requested = False
        self.last_render_time_ms = 0.0
        self.measured_server_fps = 0.0
        self.fired_count = 0

    def init_egl_scene(self):
        """Initialize VisPy with EGL backend and create the 3D scene."""
        import vispy
        vispy.use('egl')
        from vispy import scene
        from vispy.scene.visuals import Markers

        print("Initializing VisPy scene with native EGL backend...")
        self.canvas = scene.SceneCanvas(show=False, size=(self.width, self.height))
        self.view = self.canvas.central_widget.add_view()
        self.camera = scene.cameras.TurntableCamera(
            fov=45, elevation=25, azimuth=45, distance=35
        )
        self.view.camera = self.camera

        # 3D Grid
        self.grid = scene.visuals.GridLines(parent=self.view.scene, color=(0.3, 0.3, 0.3, 0.4))

        # Markers Visual
        self.markers = Markers(parent=self.view.scene)
        initial_pos = self._generate_initial_coordinates(self.n_markers)
        initial_colors = np.ones((self.n_markers, 4), dtype=np.float32)
        initial_colors[:, 0:3] = [0.2, 0.8, 1.0]
        initial_colors[:, 3] = 0.8

        self.markers.set_data(
            pos=initial_pos,
            face_color=initial_colors,
            edge_color=(1, 1, 1, 0.5),
            size=14,
            edge_width=1.0
        )

        # Initial render to instantiate OpenGL buffers
        self.canvas.render()
        parser = self.canvas.context.shared.parser
        glir_id = self.markers._vbo.id
        self.vbo_id = int(parser.get_object(glir_id).handle)
        print(f"✓ VisPy EGL initialized: OpenGL VBO handle #{self.vbo_id}")

    def _generate_initial_coordinates(self, n: int) -> np.ndarray:
        """Arrange markers along a double toroidal ring in 3D."""
        pos = np.zeros((n, 3), dtype=np.float32)
        theta = np.linspace(0, 4 * np.pi, n, endpoint=False)
        r_major = 10.0
        r_minor = 3.5
        pos[:, 0] = (r_major + r_minor * np.cos(theta * 2)) * np.cos(theta)
        pos[:, 1] = (r_major + r_minor * np.cos(theta * 2)) * np.sin(theta)
        pos[:, 2] = r_minor * np.sin(theta * 2)
        return pos

    def setup_interop_chain(self):
        """Construct the 5-link zero-copy interop chain."""
        import torch
        import pycuda.driver as cuda
        import pycuda.gl
        import numba.cuda

        print("\n" + "=" * 70)
        print("SNNgineV4 - Zero-Copy Interop Chain Setup:")
        print("=" * 70)

        torch.cuda.init()
        cuda.init()
        dev = cuda.Device(0)
        print(f"1. CUDA Device: {dev.name()} (Compute Capability {dev.compute_capability()})")
        self.cu_ctx = dev.retain_primary_context()
        self.cu_ctx.push()

        # PyCUDA RegisteredBuffer
        self.canvas.set_current()
        self.reg_buffer = pycuda.gl.RegisteredBuffer(self.vbo_id)
        mapping = self.reg_buffer.map(None)
        self.raw_ptr, mapped_size = mapping.device_ptr_and_size()
        print(f"2. PyCUDA RegisteredBuffer mapped: VRAM ptr = {hex(self.raw_ptr)}, size = {mapped_size} bytes")

        # Numba DeviceNDArray
        stride_floats = 14
        shape = (self.n_markers, stride_floats)
        strides = (stride_floats * 4, 4)
        gpu_mem = ExternalMemory(self.raw_ptr, mapped_size)

        numba_arr = numba.cuda.cudadrv.devicearray.DeviceNDArray(
            shape=shape, strides=strides, dtype=np.float32, gpu_data=gpu_mem
        )
        print(f"3. Numba DeviceNDArray: shape={numba_arr.shape}, dtype={numba_arr.dtype}")

        # PyTorch Tensor View (torch.as_tensor)
        self.gl_tensor = torch.as_tensor(numba_arr, device='cuda')
        print(f"4. PyTorch Tensor View: shape={self.gl_tensor.shape}, data_ptr={hex(self.gl_tensor.data_ptr())}")
        assert self.gl_tensor.data_ptr() == self.raw_ptr, "Pointer identity mismatch!"
        print("   ✓ Verified: PyTorch shares exact memory address with OpenGL VBO (zero-copy).")

        mapping.unmap()

        # Compile/load CUDA simulation kernel
        self._load_cuda_simulation_kernel()
        print("=" * 70 + "\n")

    def _load_cuda_simulation_kernel(self):
        """Load update_N_state from sim_demo_utils if available."""
        import torch

        sister_dir = None
        if len(parents) > 3:
            candidate = parents[3] / 'SNNgine3D_agent_branches/notebooks/simulation_demo'
            if candidate.exists():
                sister_dir = candidate
        if sister_dir is None:
            for p in sys.path:
                if (Path(p) / 'sim_demo_utils.py').exists():
                    sister_dir = Path(p)
                    break
        if sister_dir and str(sister_dir) not in sys.path:
            sys.path.insert(0, str(sister_dir))

        try:
            import sim_demo_utils
            self.sim_demo_utils = sim_demo_utils
            self.update_N_state_kernel = sim_demo_utils.update_N_state_kernel
            self.TorchHolder = sim_demo_utils.TorchHolder

            N = self.n_markers
            self.N_types = sim_demo_utils.TorchHolder((torch.rand(N).cuda() < 0.8).type(torch.int32))
            self.N_states = sim_demo_utils.make_neurons_states(N, self.N_types.tensor)
            self.fired = sim_demo_utils.TorchHolder(torch.zeros(N).cuda())
            self.r = sim_demo_utils.TorchHolder(torch.rand(N).cuda())
            self.rt = sim_demo_utils.TorchHolder(torch.ones(N).cuda())

            self.cuda_kernel_available = True
            self.use_cuda_kernel = True
            print("Link 1: Successfully compiled and loaded sister repo CUDA simulation code (update_N_state).")
        except Exception as e:
            print(f"Link 1: Warning: Could not load sim_demo_utils ({e}).")
            print("         Falling back to direct PyTorch tensor vector operations.")
            self.cuda_kernel_available = False
            self.use_cuda_kernel = False

    def step_simulation(self, dt: float):
        """Execute one simulation step and mutate VBO directly in VRAM."""
        if self.reg_buffer is None or self.gl_tensor is None:
            return

        import torch
        import pycuda.driver as cuda

        self.sim_time += dt
        self.total_steps += 1

        mapping = self.reg_buffer.map(None)
        try:
            if self.use_cuda_kernel and self.cuda_kernel_available:
                # Mode A: Sister repo CUDA simulation code
                self.r.tensor[:] = torch.rand(self.n_markers).cuda()

                block_dim = (32, 1, 1)
                grid_dim = ((self.n_markers + 31) // 32, 1)
                self.update_N_state_kernel(
                    np.int32(self.n_markers),
                    np.float32(self.sim_time),
                    self.r,
                    self.rt,
                    self.N_states,
                    self.N_types,
                    self.fired,
                    np.float32(1.0),
                    np.float32(1.0),
                    block=block_dim,
                    grid=grid_dim
                )
                cuda.Context.synchronize()

                # Zero-copy write-through: update alpha channel (index 10)
                is_fired = self.fired.tensor > 0
                self.fired_count = int(is_fired.sum().item())
                self.gl_tensor[:, 10] = torch.where(
                    is_fired,
                    torch.tensor(1.0, device='cuda'),
                    torch.tensor(0.3, device='cuda')
                )

                # Modulate marker radius / visual oscillation based on membrane potential v
                v = self.N_states.tensor[2]
                theta = 4.0 * np.pi * torch.arange(self.n_markers, device='cuda') / self.n_markers + self.sim_time * 0.3
                r_mod = 3.5 + 1.5 * ((v + 65.0) / 95.0)
                self.gl_tensor[:, 0] = (10.0 + r_mod * torch.cos(theta * 2.0)) * torch.cos(theta)
                self.gl_tensor[:, 1] = (10.0 + r_mod * torch.cos(theta * 2.0)) * torch.sin(theta)
                self.gl_tensor[:, 2] = r_mod * torch.sin(theta * 2.0)

            else:
                # Mode B: Direct PyTorch Fallback tensor operations
                idx = torch.arange(self.n_markers, device='cuda', dtype=torch.float32)
                theta = 4.0 * np.pi * idx / self.n_markers + self.sim_time * 0.5
                r_major = 10.0
                r_minor = 3.5 + 1.2 * torch.sin(self.sim_time * 1.5 + idx * 0.3)

                self.gl_tensor[:, 0] = (r_major + r_minor * torch.cos(theta * 2.0)) * torch.cos(theta)
                self.gl_tensor[:, 1] = (r_major + r_minor * torch.cos(theta * 2.0)) * torch.sin(theta)
                self.gl_tensor[:, 2] = r_minor * torch.sin(theta * 2.0)

                # Mutate color & alpha in place
                self.gl_tensor[:, 7] = 0.5 + 0.5 * torch.sin(self.sim_time + idx)
                self.gl_tensor[:, 8] = 0.5 + 0.5 * torch.cos(self.sim_time * 1.2 + idx)
                self.gl_tensor[:, 9] = 1.0
                self.gl_tensor[:, 10] = 0.4 + 0.6 * torch.abs(torch.sin(self.sim_time * 2.5 + idx))
                self.fired_count = int(self.n_markers * 0.25)

            torch.cuda.synchronize()

        except Exception as err:
            print(f"Error during step mutation: {err}")
            self.use_cuda_kernel = False

        finally:
            mapping.unmap()

    def render_frame_rgba(self) -> bytes:
        """Render scene offscreen via native EGL and return raw RGBA bytes."""
        t0 = time.perf_counter()
        img = self.canvas.render()
        t1 = time.perf_counter()
        self.last_render_time_ms = (t1 - t0) * 1000.0
        return img.tobytes()

    def get_status_dict(self) -> dict:
        """Assemble current simulation and metrics status dict."""
        return {
            "type": "status",
            "step": self.total_steps,
            "sim_time": round(self.sim_time, 2),
            "fps": round(self.measured_server_fps, 1),
            "render_time_ms": round(self.last_render_time_ms, 2),
            "paused": not self.running,
            "use_cuda_kernel": self.use_cuda_kernel,
            "cuda_kernel_available": self.cuda_kernel_available,
            "vbo_id": self.vbo_id,
            "vram_ptr": hex(self.raw_ptr) if self.raw_ptr else "N/A",
            "n_markers": self.n_markers,
            "fired_count": self.fired_count,
            "camera": {
                "azimuth": round(float(self.camera.azimuth), 1),
                "elevation": round(float(self.camera.elevation), 1),
                "distance": round(float(self.camera.distance), 1)
            }
        }

    async def handle_client_message(self, text: str):
        """Process an incoming JSON action from a connected web client."""
        try:
            msg = json.loads(text)
            action = msg.get("action")
            if action == "orbit":
                dx = float(msg.get("dx", 0.0))
                dy = float(msg.get("dy", 0.0))
                self.camera.orbit(dx, dy)
            elif action == "zoom":
                factor = float(msg.get("factor", 1.0))
                self.camera.distance = max(2.0, min(200.0, self.camera.distance * factor))
                self.camera.view_changed()
            elif action == "reset_cam":
                self.camera.azimuth = 45.0
                self.camera.elevation = 25.0
                self.camera.distance = 35.0
                self.camera.view_changed()
            elif action == "toggle_sim":
                self.running = not self.running
            elif action == "step":
                self.step_requested = True
            elif action == "toggle_mode":
                if self.cuda_kernel_available:
                    self.use_cuda_kernel = not self.use_cuda_kernel
                else:
                    self.use_cuda_kernel = False
        except Exception as err:
            print(f"Error processing client message: {err}")

    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming HTTP connection (serves web UI or upgrades to WebSocket)."""
        read_buf = bytearray()
        try:
            # Read HTTP request header
            while b"\r\n\r\n" not in read_buf and len(read_buf) < 16384:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                read_buf.extend(chunk)

            if b"\r\n\r\n" not in read_buf:
                writer.close()
                await writer.wait_closed()
                return

            header_bytes, rest = read_buf.split(b"\r\n\r\n", 1)
            lines = header_bytes.decode('utf-8', errors='ignore').split("\r\n")
            if not lines:
                writer.close()
                await writer.wait_closed()
                return

            req_line = lines[0].split(" ")
            if len(req_line) < 2:
                writer.close()
                await writer.wait_closed()
                return

            method, path = req_line[0], req_line[1]
            headers = {}
            for h in lines[1:]:
                if ":" in h:
                    k, v = h.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            # 1. WebSocket Upgrade Check
            if headers.get("upgrade", "").lower() == "websocket":
                sec_key = headers.get("sec-websocket-key")
                if not sec_key:
                    writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                    await writer.drain()
                    writer.close()
                    await writer.wait_closed()
                    return

                accept_key = compute_accept_key(sec_key)
                response = (
                    "HTTP/1.1 101 Switching Protocols\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
                )
                writer.write(response.encode('ascii'))
                await writer.drain()

                # Add client to active set
                client_entry = {"writer": writer, "reader": reader}
                self.clients.add(writer)
                print(f"[WebSocket] Client connected: {writer.get_extra_info('peername')} (Total: {len(self.clients)})")

                # Send initial init packet with dimensions
                init_msg = json.dumps({"type": "init", "width": self.width, "height": self.height})
                writer.write(make_frame(init_msg.encode('utf-8'), opcode=0x1))
                # Send immediate status
                writer.write(make_frame(json.dumps(self.get_status_dict()).encode('utf-8'), opcode=0x1))
                await writer.drain()

                # WebSocket receive loop
                ws_buf = bytearray(rest)
                while True:
                    while True:
                        parsed = parse_client_frame(ws_buf)
                        if parsed is None:
                            break
                        opcode, payload, consumed = parsed
                        del ws_buf[:consumed]
                        if opcode == 0x8:  # Close
                            raise ConnectionResetError("Client sent close frame")
                        elif opcode == 0x9:  # Ping -> Pong
                            writer.write(make_frame(payload, opcode=0xA))
                            await writer.drain()
                        elif opcode == 0x1:  # Text
                            await self.handle_client_message(payload.decode('utf-8', errors='ignore'))

                    chunk = await reader.read(65536)
                    if not chunk:
                        break
                    ws_buf.extend(chunk)

                return

            # 2. HTTP Health Probe
            if path in ("/health", "/status"):
                status_json = json.dumps(self.get_status_dict()).encode('utf-8')
                resp = (
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: application/json\r\n"
                    b"Access-Control-Allow-Origin: *\r\n"
                    + f"Content-Length: {len(status_json)}\r\n\r\n".encode('ascii')
                    + status_json
                )
                writer.write(resp)
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return

            # 3. HTTP Web Interface (GET / or /index.html)
            html_bytes = HTML_PAGE.encode('utf-8')
            resp = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/html; charset=utf-8\r\n"
                + f"Content-Length: {len(html_bytes)}\r\n\r\n".encode('ascii')
                + html_bytes
            )
            writer.write(resp)
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
            pass
        except Exception as e:
            print(f"[Server] Connection error: {e}")
        finally:
            if writer in self.clients:
                self.clients.remove(writer)
                print(f"[WebSocket] Client disconnected (Remaining: {len(self.clients)})")
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def broadcast_loop(self):
        """Main rendering, simulation step, and WebSocket broadcast loop."""
        interval = 1.0 / self.target_fps
        frame_counter = 0
        fps_start = time.perf_counter()

        start_time = time.time()

        while True:
            t_loop_start = time.perf_counter()

            if self.timeout is not None and (time.time() - start_time) >= self.timeout:
                print(f"[Server] Timeout limit ({self.timeout}s) reached. Shutting down cleanly...")
                break

            # 1. Step simulation
            if self.running or self.step_requested:
                self.step_simulation(interval)
                self.step_requested = False

            # 2. Render frame
            rgba_bytes = self.render_frame_rgba()
            frame_counter += 1

            # Compute measured FPS every 1 second
            now = time.perf_counter()
            elapsed_fps = now - fps_start
            if elapsed_fps >= 1.0:
                self.measured_server_fps = frame_counter / elapsed_fps
                frame_counter = 0
                fps_start = now
                if self.total_steps % 60 == 0:
                    mode_name = "CUDA (update_N_state)" if self.use_cuda_kernel else "PyTorch Fallback"
                    print(f"[Loop] Step: {self.total_steps:04d} | Mode: {mode_name} | "
                          f"FPS: {self.measured_server_fps:.1f} | Render: {self.last_render_time_ms:.1f}ms | "
                          f"Clients: {len(self.clients)}")

            # 3. Broadcast to connected WebSocket clients
            if self.clients:
                bin_frame = make_frame(rgba_bytes, opcode=0x2)
                status_dict = self.get_status_dict()
                txt_frame = make_frame(json.dumps(status_dict).encode('utf-8'), opcode=0x1)

                dead_clients = set()
                for client in list(self.clients):
                    try:
                        # Drop frame if client write buffer is backlogged (> 4MB) to prevent latency
                        buf_size = client.transport.get_write_buffer_size()
                        if buf_size < 4 * 1024 * 1024:
                            client.write(bin_frame)
                            client.write(txt_frame)
                        else:
                            # Send only status to backlogged client
                            client.write(txt_frame)
                    except Exception:
                        dead_clients.add(client)

                for dc in dead_clients:
                    if dc in self.clients:
                        self.clients.remove(dc)

            # Sleep remainder of frame budget
            loop_duration = time.perf_counter() - t_loop_start
            sleep_duration = max(0.001, interval - loop_duration)
            await asyncio.sleep(sleep_duration)

    def cleanup(self):
        """Tear down OpenGL and CUDA contexts cleanly."""
        print("[Server] Cleaning up CUDA & EGL resources...")
        if self.reg_buffer is not None:
            try:
                self.reg_buffer.unregister()
            except Exception:
                pass
        if self.cu_ctx is not None:
            try:
                self.cu_ctx.pop()
            except Exception:
                pass
        print("[Server] Cleanup complete.")


async def main_async(args):
    server = WebInteropServer(
        host=args.host,
        port=args.port,
        width=args.width,
        height=args.height,
        fps=args.fps,
        n_markers=args.markers,
        timeout=args.timeout
    )

    server.init_egl_scene()
    server.setup_interop_chain()

    # Start asyncio TCP server
    tcp_server = await asyncio.start_server(
        server.handle_connection,
        server.host,
        server.port
    )

    print("=" * 70)
    print(f"🚀 SNNgineV4 Zero-Copy Web Bridge Server Running!")
    print(f"   Address: http://{server.host}:{server.port}")
    print(f"   Canvas:  {server.width}x{server.height} @ {server.target_fps} FPS target")
    print(f"   Markers: {server.n_markers} (double torus)")
    print("=" * 70)
    print("\nVisual verification instructions:")
    print("  1. Open http://localhost:6080 in any web browser.")
    print("  2. Observe the 3D double torus rotating with live neuron firing pulses.")
    print("  3. Drag mouse / touch to orbit camera; scroll to zoom.")
    print("  4. Click 'Switch to PyTorch Fallback' to verify Links 2-5 zero-copy mutations.")
    print("  5. Click 'Pause Simulation' to inspect static coordinates, then 'Resume'.")
    print("\nPress Ctrl+C to terminate.")

    try:
        async with tcp_server:
            await server.broadcast_loop()
    except asyncio.CancelledError:
        pass
    finally:
        server.cleanup()


def main():
    parser = argparse.ArgumentParser(description="SNNgineV4 Interactive Web Bridge (Phase 4)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=6080, help="Port to listen on (default: 6080)")
    parser.add_argument("--fps", type=int, default=30, help="Target FPS (default: 30)")
    parser.add_argument("--markers", type=int, default=64, help="Marker count (default: 64)")
    parser.add_argument("--width", type=int, default=800, help="Render width (default: 800)")
    parser.add_argument("--height", type=int, default=600, help="Render height (default: 600)")
    parser.add_argument("--timeout", type=float, default=None, help="Auto-close server after N seconds (for testing)")
    args = parser.parse_args()

    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\nShutdown requested by user. Exiting cleanly.")


if __name__ == '__main__':
    main()
