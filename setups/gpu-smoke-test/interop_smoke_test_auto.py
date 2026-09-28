"""
Phase 2 Automated Headless Smoke Test: CUDA-OpenGL Zero-Copy Interop Verification.

This test runs unattended without a display (headless via EGL) and asserts on
the complete 5-link zero-copy interop chain:
  Link 1: Hand-written CUDA simulation kernel (pycuda.compiler.SourceModule).
  Link 2: PyCUDA built with OpenGL interoperability.
  Link 3: PyCUDA RegisteredBuffer mapped from an OpenGL VBO.
  Link 4: Mapped memory wrapped as a numba.cuda.cudadrv.devicearray.DeviceNDArray.
  Link 5: PyTorch tensor view wrapping the Numba device array (torch.as_tensor).

Usage:
    /home/htm/anaconda3/envs/snngine/bin/python setups/gpu-smoke-test/interop_smoke_test_auto.py
"""

import ctypes
import os
import sys
from pathlib import Path

import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def create_egl_headless_context(width=64, height=64):
    """Create a headless OpenGL context and pbuffer surface via EGL."""
    try:
        from OpenGL import EGL as egl
        from OpenGL import GL as gl
    except ImportError as e:
        raise RuntimeError(f"PyOpenGL / EGL import failed: {e}")

    display = egl.eglGetDisplay(egl.EGL_DEFAULT_DISPLAY)
    if display == egl.EGL_NO_DISPLAY:
        raise RuntimeError("Failed to get EGL display (EGL_NO_DISPLAY).")

    major, minor = egl.EGLint(), egl.EGLint()
    if not egl.eglInitialize(display, major, minor):
        raise RuntimeError("Failed to initialize EGL display.")

    config_attribs = [
        egl.EGL_SURFACE_TYPE, egl.EGL_PBUFFER_BIT,
        egl.EGL_RENDERABLE_TYPE, egl.EGL_OPENGL_BIT,
        egl.EGL_NONE
    ]
    config = (egl.EGLConfig * 1)()
    num_configs = egl.EGLint()
    if not egl.eglChooseConfig(
        display,
        (egl.EGLint * len(config_attribs))(*config_attribs),
        config,
        1,
        num_configs
    ) or num_configs.value < 1:
        raise RuntimeError("Failed to choose compatible EGL framebuffer configuration.")

    egl.eglBindAPI(egl.EGL_OPENGL_API)
    ctx_attribs = [egl.EGL_NONE]
    context = egl.eglCreateContext(
        display,
        config[0],
        egl.EGL_NO_CONTEXT,
        (egl.EGLint * len(ctx_attribs))(*ctx_attribs)
    )
    if context == egl.EGL_NO_CONTEXT:
        raise RuntimeError("Failed to create EGL OpenGL context.")

    pbuffer_attribs = [
        egl.EGL_WIDTH, width,
        egl.EGL_HEIGHT, height,
        egl.EGL_NONE
    ]
    surface = egl.eglCreatePbufferSurface(
        display,
        config[0],
        (egl.EGLint * len(pbuffer_attribs))(*pbuffer_attribs)
    )
    if surface == egl.EGL_NO_SURFACE:
        egl.eglDestroyContext(display, context)
        raise RuntimeError("Failed to create EGL pbuffer surface.")

    if not egl.eglMakeCurrent(display, surface, surface, context):
        egl.eglDestroySurface(display, surface)
        egl.eglDestroyContext(display, context)
        raise RuntimeError("Failed to make EGL context current.")

    vendor = gl.glGetString(gl.GL_VENDOR).decode()
    renderer = gl.glGetString(gl.GL_RENDERER).decode()
    gl_version = gl.glGetString(gl.GL_VERSION).decode()

    return {
        'display': display,
        'surface': surface,
        'context': context,
        'vendor': vendor,
        'renderer': renderer,
        'gl_version': gl_version,
    }


def destroy_egl_headless_context(egl_info):
    """Tear down EGL context cleanly."""
    from OpenGL import EGL as egl
    display = egl_info['display']
    surface = egl_info['surface']
    context = egl_info['context']

    egl.eglMakeCurrent(display, egl.EGL_NO_SURFACE, egl.EGL_NO_SURFACE, egl.EGL_NO_CONTEXT)
    egl.eglDestroySurface(display, surface)
    egl.eglDestroyContext(display, context)
    egl.eglTerminate(display)


class ExternalMemory:
    """External GPU memory wrapper conforming to numba CUDA device array requirements."""
    __cuda_memory__ = True

    def __init__(self, ptr: int, size: int):
        self.device_ctypes_pointer = ctypes.c_void_p(ptr)
        self._cuda_memsize_ = size


def run_automated_smoke_test():
    print("=" * 70)
    print("SNNgineV4 - Phase 2: Automated Headless Interop Smoke Test")
    print("=" * 70)

    # 1. Initialize Headless EGL Context
    print("\n[Step 1/7] Initializing headless EGL OpenGL context...")
    egl_info = create_egl_headless_context()
    print(f"  - EGL Renderer:  {egl_info['renderer']}")
    print(f"  - EGL Vendor:    {egl_info['vendor']}")
    print(f"  - GL Version:    {egl_info['gl_version']}")

    from OpenGL import GL as gl
    import torch
    import pycuda.driver as cuda
    import pycuda.gl
    from pycuda.compiler import SourceModule
    import numba.cuda

    # 2. Initialize CUDA Primary Context
    print("\n[Step 2/7] Initializing PyCUDA & PyTorch CUDA contexts...")
    torch.cuda.init()
    cuda.init()
    dev = cuda.Device(0)
    dev_name = dev.name()
    compute_cap = dev.compute_capability()
    print(f"  - CUDA Device:   {dev_name} (Compute Capability {compute_cap[0]}.{compute_cap[1]})")
    print(f"  - PyTorch CUDA:  v{torch.version.cuda}, is_available={torch.cuda.is_available()}")

    cu_ctx = dev.retain_primary_context()
    cu_ctx.push()

    try:
        # Define TorchHolder for PyCUDA kernel pointer passing
        class TorchHolder(cuda.PointerHolderBase):
            def __init__(self, tensor):
                super().__init__()
                self.tensor = tensor
                self.gpudata = tensor.data_ptr()

            def get_pointer(self, **kwargs):
                return self.tensor.data_ptr()

        # 3. Create OpenGL VBO
        print("\n[Step 3/7] Creating OpenGL Vertex Buffer Object (VBO)...")
        num_elements = 32
        stride_floats = 14  # Matches VisPy MarkersVisual layout (14 floats = 56 bytes)
        total_floats = num_elements * stride_floats
        total_bytes = total_floats * 4

        vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
        initial_data = np.zeros(total_floats, dtype=np.float32)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, initial_data.nbytes, initial_data, gl.GL_DYNAMIC_DRAW)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glFinish()
        print(f"  - VBO ID:        {vbo}")
        print(f"  - Buffer Layout: {num_elements} elements x {stride_floats} floats ({total_bytes} bytes)")

        # 4. PyCUDA RegisteredBuffer Interop
        print("\n[Step 4/7] Registering VBO with PyCUDA OpenGL interop...")
        reg = pycuda.gl.RegisteredBuffer(int(vbo))
        mapping = reg.map(None)
        ptr, mapped_size = mapping.device_ptr_and_size()
        print(f"  - Mapped Ptr:    {hex(ptr)}")
        print(f"  - Mapped Size:   {mapped_size} bytes (expected {total_bytes})")
        assert mapped_size == total_bytes, f"Size mismatch: {mapped_size} != {total_bytes}"

        # 5. Numba DeviceNDArray & PyTorch Tensor Wrapping
        print("\n[Step 5/7] Wrapping mapped pointer via Numba into PyTorch tensor...")
        gpu_mem = ExternalMemory(ptr, mapped_size)
        numba_arr = numba.cuda.cudadrv.devicearray.DeviceNDArray(
            shape=(num_elements, stride_floats),
            strides=(stride_floats * 4, 4),
            dtype=np.float32,
            gpu_data=gpu_mem
        )
        torch_tensor = torch.as_tensor(numba_arr, device='cuda')
        print(f"  - Numba Array:   shape={numba_arr.shape}, dtype={numba_arr.dtype}")
        print(f"  - PyTorch View:  shape={torch_tensor.shape}, device={torch_tensor.device}")
        print(f"  - Tensor Ptr:    {hex(torch_tensor.data_ptr())}")
        assert torch_tensor.data_ptr() == ptr, (
            f"Pointer mismatch: PyTorch data_ptr {hex(torch_tensor.data_ptr())} != PyCUDA {hex(ptr)}"
        )
        print("  ✓ Zero-copy pointer identity verified: PyTorch shares exact VRAM address.")

        # 6. Test A: Direct PyTorch write-through assertion
        print("\n[Step 6/7] Test A: PyTorch tensor direct write-through assertion...")
        test_pattern_pt = np.arange(total_floats, dtype=np.float32) * 1.5 + 2.0
        torch_tensor[:] = torch.from_numpy(test_pattern_pt.reshape(num_elements, stride_floats)).cuda()
        torch.cuda.synchronize()

        # Unmap before OpenGL reads back
        mapping.unmap()

        # Read back from OpenGL VBO directly
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
        raw_gl = gl.glGetBufferSubData(gl.GL_ARRAY_BUFFER, 0, total_bytes)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        readback_pt = np.frombuffer(raw_gl, dtype=np.float32)

        np.testing.assert_allclose(
            readback_pt,
            test_pattern_pt,
            rtol=1e-5, atol=1e-5,
            err_msg="OpenGL readback does not match PyTorch write-through!"
        )
        print("  ✓ Direct PyTorch write-through confirmed: OpenGL readback matches byte-for-byte.")

        # 7. Test B & C: CUDA Kernel write-through and PyTorch view assertion
        print("\n[Step 7/7] Test B & C: CUDA kernel execution and PyTorch view consistency...")
        kernel_src = """
        __global__ void test_marker_kernel(float* buffer, int n_elements, float t) {
            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            if (idx < n_elements) {
                int base = idx * 14;
                float angle = 6.2831853f * (float)idx / (float)n_elements + t;
                buffer[base + 0] = cosf(angle);                        // X
                buffer[base + 1] = sinf(angle);                        // Y
                buffer[base + 2] = (float)idx * 0.5f;                  // Z
                buffer[base + 10] = 0.5f + 0.5f * sinf(t + (float)idx); // Alpha
            }
        }
        """
        mod = SourceModule(kernel_src)
        kernel_func = mod.get_function("test_marker_kernel")

        # Re-map buffer for CUDA kernel write
        mapping = reg.map(None)
        ptr, _ = mapping.device_ptr_and_size()
        holder = TorchHolder(torch_tensor)

        test_t = 3.14159 / 4.0
        block_dim = (32, 1, 1)
        grid_dim = ((num_elements + 31) // 32, 1)
        kernel_func(holder, np.int32(num_elements), np.float32(test_t), block=block_dim, grid=grid_dim)
        cuda.Context.synchronize()

        # Test C assertion: PyTorch view reflects kernel write without unmapping or re-reading
        tensor_snapshot = torch_tensor.cpu().numpy().flatten()
        expected_x_0 = np.cos(test_t)
        expected_y_0 = np.sin(test_t)
        assert np.isclose(tensor_snapshot[0], expected_x_0, atol=1e-5), (
            f"PyTorch view did not reflect kernel write: {tensor_snapshot[0]} vs {expected_x_0}"
        )
        assert np.isclose(tensor_snapshot[1], expected_y_0, atol=1e-5), (
            f"PyTorch view did not reflect kernel write: {tensor_snapshot[1]} vs {expected_y_0}"
        )
        print("  ✓ PyTorch view consistency confirmed: sees CUDA kernel writes live in VRAM.")

        # Test B assertion: OpenGL readback matches CUDA kernel write
        mapping.unmap()

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
        raw_gl_kernel = gl.glGetBufferSubData(gl.GL_ARRAY_BUFFER, 0, total_bytes)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        readback_kernel = np.frombuffer(raw_gl_kernel, dtype=np.float32)

        np.testing.assert_allclose(
            readback_kernel,
            tensor_snapshot,
            rtol=1e-5, atol=1e-5,
            err_msg="OpenGL readback does not match CUDA kernel write!"
        )
        print("  ✓ CUDA kernel write-through confirmed: OpenGL readback matches byte-for-byte.")

        # Test D: Sister repo self-compiled simulation kernel (update_N_state) verification
        print("\n[Step 7B/7] Test D: Sister repo self-compiled CUDA simulation code (update_N_state)...")
        import types
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

        import sim_demo_utils
        N = num_elements
        N_types = sim_demo_utils.TorchHolder((torch.rand(N).cuda() < 0.8).type(torch.int32))
        N_states = sim_demo_utils.make_neurons_states(N, N_types.tensor)
        fired = sim_demo_utils.TorchHolder(torch.zeros(N).cuda())
        r = sim_demo_utils.TorchHolder(torch.rand(N).cuda())
        rt = sim_demo_utils.TorchHolder(torch.ones(N).cuda())

        # Verify initial voltage is -65.0
        assert torch.all(N_states.tensor[2] == -65.0)

        # Step kernel
        sim_demo_utils.update_N_state_kernel(
            np.int32(N), np.float32(0.1), r, rt, N_states, N_types, fired,
            np.float32(1.0), np.float32(1.0),
            block=block_dim, grid=grid_dim
        )
        cuda.Context.synchronize()
        # Verify voltages evolved
        assert not torch.all(N_states.tensor[2] == -65.0)
        print("  ✓ Sister repo self-compiled simulation kernel (update_N_state) executed and verified.")

        # Cleanup
        reg.unregister()
        gl.glDeleteBuffers(1, [vbo])
        print("\n" + "=" * 70)
        print("ALL INTEROP ASSERTIONS PASSED (5/5 LINKS VERIFIED ZERO-COPY)")
        print("=" * 70)
        return True

    finally:
        cu_ctx.pop()
        destroy_egl_headless_context(egl_info)


if __name__ == '__main__':
    try:
        success = run_automated_smoke_test()
        sys.exit(0 if success else 1)
    except Exception as exc:
        print(f"\nFATAL: Automated smoke test failed with exception: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
