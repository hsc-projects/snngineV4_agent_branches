"""
Phase 1 Smoke Test: Standalone CUDA-OpenGL Zero-Copy Interoperability Visual Check.

Exercises the real 5-link zero-copy interop chain without the SNNgineV4 config/network/GUI stack:
  Link 1: Hand-written CUDA simulation code (compiled via pycuda.compiler.SourceModule).
  Link 2: PyCUDA built with OpenGL interoperability (pycuda.gl).
  Link 3: PyCUDA RegisteredBuffer mapped directly from VisPy's OpenGL VBO.
  Link 4: Mapped device pointer wrapped as a numba.cuda.cudadrv.devicearray.DeviceNDArray.
  Link 5: PyTorch tensor view wrapping the Numba device array (torch.as_tensor).

Features:
  - Live write-through verification: per-frame buffer mutations occur purely in VRAM with
    zero CPU-GPU copies and no VisPy set_data() calls.
  - Optional CUDA kernel step with seamless fallback: maintainer can dynamically toggle
    between the compiled CUDA kernel (Link 1) and direct PyTorch tensor vector operations.
  - Interactive 3D scene (VisPy TurntableCamera) displaying 64 animated markers.

Usage (Maintainer visual launch):
    DISPLAY=:1 /home/htm/anaconda3/envs/snngine/bin/python setups/gpu-smoke-test/interop_smoke_test_standalone_gui.py
"""

import ctypes
import os
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure display and Qt GLX integration defaults
if 'DISPLAY' not in os.environ:
    os.environ['DISPLAY'] = ':1'
os.environ.setdefault('QT_XCB_GL_INTEGRATION', 'glx')

import numpy as np
from qtpy import QtCore, QtWidgets
from vispy import scene
from vispy.scene.visuals import Markers


class ExternalMemory:
    """External GPU memory wrapper conforming to Numba CUDA device array requirements."""
    __cuda_memory__ = True

    def __init__(self, ptr: int, size: int):
        self.device_ctypes_pointer = ctypes.c_void_p(ptr)
        self._cuda_memsize_ = size


class StandaloneInteropWindow(QtWidgets.QMainWindow):
    """
    Self-contained Qt Window displaying a VisPy 3D scene driven by CUDA/PyTorch VBO interop.
    """

    def __init__(self, n_markers: int = 64):
        super().__init__()
        self.n_markers = n_markers
        self.total_steps = 0
        self.sim_time = 0.0
        self.use_cuda_kernel = True
        self.cuda_kernel_available = False
        self.cu_ctx = None
        self.reg_buffer = None
        self.gl_tensor = None
        self.raw_ptr = None
        self.vbo_id = None

        self.setWindowTitle("SNNgineV4 - Standalone Interop Smoke Test (Phase 1)")
        self.resize(1100, 800)

        # Main widget & layout
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. VisPy 3D SceneCanvas
        self.canvas = scene.SceneCanvas(keys='interactive', show=False)
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = scene.cameras.TurntableCamera(
            fov=45, elevation=25, azimuth=45, distance=35
        )

        # Add 3D grid / visual cues
        self.grid = scene.visuals.GridLines(parent=self.view.scene, color=(0.3, 0.3, 0.3, 0.4))

        # Add Markers Visual
        # VisPy MarkersVisual layout: 14 floats per marker (pos[3], fg[4], bg[4], size[1], edgewidth[1], symbol[1])
        self.markers = Markers(parent=self.view.scene)
        initial_pos = self._generate_initial_coordinates(self.n_markers)
        initial_colors = np.ones((self.n_markers, 4), dtype=np.float32)
        initial_colors[:, 0:3] = [0.2, 0.8, 1.0]  # Cyan-blue default
        initial_colors[:, 3] = 0.8               # Alpha

        self.markers.set_data(
            pos=initial_pos,
            face_color=initial_colors,
            edge_color=(1, 1, 1, 0.5),
            size=14,
            edge_width=1.0
        )
        main_layout.addWidget(self.canvas.native)

        # 2. Control Toolbar
        control_panel = QtWidgets.QFrame(self)
        control_panel.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")
        bar_layout = QtWidgets.QHBoxLayout(control_panel)
        bar_layout.setContentsMargins(12, 8, 12, 8)
        bar_layout.setSpacing(10)

        self.btn_toggle_sim = QtWidgets.QPushButton("Pause Simulation")
        self.btn_toggle_sim.setCheckable(True)
        self.btn_toggle_sim.setChecked(True)
        self.btn_toggle_sim.clicked.connect(self._toggle_simulation)
        bar_layout.addWidget(self.btn_toggle_sim)

        self.btn_step = QtWidgets.QPushButton("Step (1 frame)")
        self.btn_step.clicked.connect(lambda: self._step_frame(0.05))
        bar_layout.addWidget(self.btn_step)

        self.btn_toggle_mode = QtWidgets.QPushButton("Switch to PyTorch Fallback")
        self.btn_toggle_mode.clicked.connect(self._toggle_kernel_mode)
        bar_layout.addWidget(self.btn_toggle_mode)

        self.lbl_status = QtWidgets.QLabel("Status: Initializing interop chain...")
        self.lbl_status.setStyleSheet("font-family: monospace; font-size: 12px; color: #a0ffa0;")
        bar_layout.addWidget(self.lbl_status)

        bar_layout.addStretch()

        self.btn_exit = QtWidgets.QPushButton("Exit")
        self.btn_exit.clicked.connect(self.close)
        bar_layout.addWidget(self.btn_exit)

        main_layout.addWidget(control_panel)

        # Animation timer (~33 FPS)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(lambda: self._step_frame(0.04))

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
        """
        Build and verify the complete 5-link zero-copy interop chain:
        OpenGL VBO -> PyCUDA RegisteredBuffer -> Numba DeviceNDArray -> PyTorch Tensor.
        """
        print("\n" + "=" * 70)
        print("SNNgineV4 - Standalone Interop Chain Setup:")
        print("=" * 70)

        import torch
        import pycuda.driver as cuda
        import pycuda.gl
        from pycuda.compiler import SourceModule
        import numba.cuda

        # 1. Trigger initial VisPy render to generate OpenGL buffer handle
        self.canvas.render()
        parser = self.canvas.context.shared.parser
        glir_id = self.markers._vbo.id
        self.vbo_id = int(parser.get_object(glir_id).handle)
        print(f"1. OpenGL VBO generated via VisPy: ID = {self.vbo_id}")

        # 2. CUDA & PyCUDA Primary Context
        torch.cuda.init()
        cuda.init()
        dev = cuda.Device(0)
        print(f"2. CUDA Device: {dev.name()} (Compute Capability {dev.compute_capability()})")
        self.cu_ctx = dev.retain_primary_context()
        self.cu_ctx.push()

        # 3. PyCUDA RegisteredBuffer
        self.reg_buffer = pycuda.gl.RegisteredBuffer(self.vbo_id)
        mapping = self.reg_buffer.map(None)
        self.raw_ptr, mapped_size = mapping.device_ptr_and_size()
        print(f"3. PyCUDA RegisteredBuffer mapped: VRAM ptr = {hex(self.raw_ptr)}, size = {mapped_size} bytes")

        # 4. Numba DeviceNDArray
        stride_floats = 14
        shape = (self.n_markers, stride_floats)
        strides = (stride_floats * 4, 4)
        gpu_mem = ExternalMemory(self.raw_ptr, mapped_size)

        numba_arr = numba.cuda.cudadrv.devicearray.DeviceNDArray(
            shape=shape, strides=strides, dtype=np.float32, gpu_data=gpu_mem
        )
        print(f"4. Numba DeviceNDArray: shape={numba_arr.shape}, dtype={numba_arr.dtype}")

        # 5. PyTorch Tensor View (torch.as_tensor)
        self.gl_tensor = torch.as_tensor(numba_arr, device='cuda')
        print(f"5. PyTorch Tensor View: shape={self.gl_tensor.shape}, device={self.gl_tensor.device}")
        print(f"   Tensor data_ptr = {hex(self.gl_tensor.data_ptr())}")
        assert self.gl_tensor.data_ptr() == self.raw_ptr, "Pointer identity mismatch!"
        print("   ✓ Verified: PyTorch shares exact memory address with OpenGL VBO (zero-copy).")

        mapping.unmap()

        # Compile CUDA Kernel (Link 1)
        self._compile_cuda_kernel()

        # Start live animation
        self.timer.start(30)
        self._update_status_display()
        print("=" * 70 + "\n")

    def _compile_cuda_kernel(self):
        """Load the sister repo's self-compiled CUDA simulation code (update_N_state)."""
        import types
        from pathlib import Path
        import torch
        import pycuda.driver as cuda

        # Stub IPython.display if not installed so sim_demo_utils can import cleanly
        if 'IPython' not in sys.modules:
            ipython = types.ModuleType('IPython')
            ipython_display = types.ModuleType('IPython.display')
            ipython_display.display_html = lambda *a, **k: None
            ipython.display = ipython_display
            sys.modules['IPython'] = ipython
            sys.modules['IPython.display'] = ipython_display

        sister_dir = Path(__file__).resolve().parents[3] / 'SNNgine3D_agent_branches/notebooks/simulation_demo'
        if str(sister_dir) not in sys.path:
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
            print("Link 1: Successfully integrated self-compiled CUDA simulation code (update_N_state from sim_demo_utils).")
        except Exception as e:
            print(f"Link 1: Warning: Failed to load sim_demo_utils: {e}")
            print("Falling back to direct PyTorch tensor vector operations.")
            self.cuda_kernel_available = False
            self.use_cuda_kernel = False

    def _step_frame(self, dt: float):
        """Execute one live simulation step and mutate the VBO directly in VRAM."""
        if self.reg_buffer is None or self.gl_tensor is None:
            return

        import torch
        import pycuda.driver as cuda

        self.sim_time += dt
        self.total_steps += 1

        # 1. Map OpenGL buffer for CUDA access
        mapping = self.reg_buffer.map(None)

        try:
            if self.use_cuda_kernel and self.cuda_kernel_available:
                # Mode A: Hand-written CUDA simulation kernel execution (update_N_state)
                # Resets random thalamic input each step
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

                # Zero-copy write-through to VisPy marker buffer:
                # Update alpha channel (float index 10) based on neuron firing state
                # (matching snn_simulation.cu line 41/112 & vertical-trace.md: 1.0 on fire, 0.3 resting)
                is_fired = self.fired.tensor > 0
                self.gl_tensor[:, 10] = torch.where(
                    is_fired,
                    torch.tensor(1.0, device='cuda'),
                    torch.tensor(0.3, device='cuda')
                )

                # Modulate marker radius / visual oscillation based on membrane voltage v (row 2 of N_states)
                v = self.N_states.tensor[2]  # membrane potential, typically -65mV to +30mV
                theta = 4.0 * np.pi * torch.arange(self.n_markers, device='cuda') / self.n_markers + self.sim_time * 0.3
                r_mod = 3.5 + 1.5 * ((v + 65.0) / 95.0)  # expands on depolarization
                self.gl_tensor[:, 0] = (10.0 + r_mod * torch.cos(theta * 2.0)) * torch.cos(theta)
                self.gl_tensor[:, 1] = (10.0 + r_mod * torch.cos(theta * 2.0)) * torch.sin(theta)
                self.gl_tensor[:, 2] = r_mod * torch.sin(theta * 2.0)

            else:
                # Mode B: PyTorch Fallback tensor operations (Links 2-5)
                idx = torch.arange(self.n_markers, device='cuda', dtype=torch.float32)
                theta = 4.0 * np.pi * idx / self.n_markers + self.sim_time * 0.5
                r_major = 10.0
                r_minor = 3.5 + 1.2 * torch.sin(self.sim_time * 1.5 + idx * 0.3)

                # Mutate 3D coordinates in place
                self.gl_tensor[:, 0] = (r_major + r_minor * torch.cos(theta * 2.0)) * torch.cos(theta)
                self.gl_tensor[:, 1] = (r_major + r_minor * torch.cos(theta * 2.0)) * torch.sin(theta)
                self.gl_tensor[:, 2] = r_minor * torch.sin(theta * 2.0)

                # Mutate color & alpha in place (a_bg_color offset: 7..10)
                self.gl_tensor[:, 7] = 0.5 + 0.5 * torch.sin(self.sim_time + idx)
                self.gl_tensor[:, 8] = 0.5 + 0.5 * torch.cos(self.sim_time * 1.2 + idx)
                self.gl_tensor[:, 9] = 1.0
                self.gl_tensor[:, 10] = 0.4 + 0.6 * torch.abs(torch.sin(self.sim_time * 2.5 + idx))

            torch.cuda.synchronize()

        except Exception as err:
            print(f"Error during step mutation: {err}")
            # Automatically fallback to PyTorch if kernel crashes
            self.use_cuda_kernel = False
            self._update_status_display()

        finally:
            # 2. Unmap buffer before OpenGL draws
            mapping.unmap()

        # 3. Request visual redraw (VisPy reads directly from mutated VBO)
        self.canvas.update()
        if self.total_steps % 30 == 0:
            self._update_status_display()

    def _toggle_simulation(self):
        if self.btn_toggle_sim.isChecked():
            self.btn_toggle_sim.setText("Pause Simulation")
            self.timer.start(30)
        else:
            self.btn_toggle_sim.setText("Resume Simulation")
            self.timer.stop()

    def _toggle_kernel_mode(self):
        if not self.cuda_kernel_available:
            self.use_cuda_kernel = False
            self.btn_toggle_mode.setEnabled(False)
            return

        self.use_cuda_kernel = not self.use_cuda_kernel
        if self.use_cuda_kernel:
            self.btn_toggle_mode.setText("Switch to PyTorch Fallback")
        else:
            self.btn_toggle_mode.setText("Switch to CUDA Kernel")
        self._update_status_display()

    def _update_status_display(self):
        mode_str = "CUDA (sim_demo_utils update_N_state)" if self.use_cuda_kernel else "PyTorch Fallback (Links 2-5)"
        status_text = (
            f"Step: {self.total_steps:04d} | Mode: {mode_str} | "
            f"VBO: #{self.vbo_id} | VRAM: {hex(self.raw_ptr) if self.raw_ptr else 'N/A'}"
        )
        self.lbl_status.setText(status_text)

    def closeEvent(self, event):
        """Clean teardown on window exit."""
        self.timer.stop()
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
        super().closeEvent(event)


def main():
    print("=" * 70)
    print("Launching SNNgineV4 Standalone Interop Smoke Test (Phase 1 Visual Check)")
    print("=" * 70)
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    window = StandaloneInteropWindow(n_markers=64)
    window.show()
    app.processEvents()

    # Initialize CUDA-OpenGL interop after surface/window is shown and mapped
    QtCore.QTimer.singleShot(100, window.setup_interop_chain)

    print("\nApplication window is open.")
    print("Visual verification instructions for maintainer:")
    print("  1. Observe the 64 3D markers rotating smoothly in a dual-ring torus.")
    print("  2. Verify that markers dynamically pulse in brightness and color.")
    print("  3. Click 'Switch to PyTorch Fallback' to confirm Links 2-5 mutate the buffer equally.")
    print("  4. Click 'Pause Simulation' to inspect static coordinates, then 'Resume'.")
    print("  5. Notice that zero set_data() calls are made: rendering occurs solely via direct VRAM mutation.")
    print("\nPress Ctrl+C or close window to exit.")
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
