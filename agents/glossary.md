# Glossary

Terms defined once here instead of being re-explained inline each time.

## CUDA/OpenGL interoperability

CUDA supports interoperating with graphics APIs like OpenGL. To do this, an
OpenGL resource (a buffer or texture) is *registered* and *mapped* into
CUDA's address space, giving CUDA a raw device pointer (or texture handle)
that refers to the same GPU memory OpenGL owns, rather than a separate copy.
A CUDA kernel can then read/write that memory directly, and the results are
immediately visible to OpenGL's renderer once the mapping is undone
(mapping must be unmapped before OpenGL's own rendering pipeline touches
the resource again, to avoid undefined behavior).

This is what makes **zero-copy** interop possible. Since both CUDA and
OpenGL refer to the same physical GPU memory, data written by a CUDA
kernel can be rendered by OpenGL without being copied through host (CPU)
memory, and without a separate GPU-to-GPU copy either. It's the same
bytes, accessed by two different APIs. Contrast with the project's
3D-texture case, documented in `agents/common.md` → Core technical facts,
where this zero-copy mapping was not achieved and an explicit
`pycuda.driver.Memcpy3D` GPU-to-GPU copy is used instead.

Sources:
[3D Game Engine Programming](https://www.3dgep.com/opengl-interoperability-with-cuda/),
[Medium — CUDA: OpenGL interop](https://medium.com/@fatlip/cuda-opengl-interop-e4edd8727c63)

## Warp, warp divergence

A **warp** is a group of 32 threads that a CUDA GPU schedules and executes
together, one shared instruction at a time (SIMT: Single-Instruction,
Multiple-Thread). 32 is a hardware constant across all NVIDIA CUDA
architectures.

**Warp divergence** occurs when threads within the same warp take
different paths at a data-dependent conditional branch. The warp cannot
run both paths at once: it executes each path serially, disabling the
threads not on that path, then reconverges once all paths complete. Full
efficiency requires all 32 threads in a warp to agree on their execution
path; divergence increases the total instructions executed for that warp.
Divergence only happens within a warp; separate warps run independently of
each other regardless of what path each takes.

In this project, this is why every neuron has the same fixed synapse
count: if one thread processed one neuron's synapses, a neuron with far
fewer synapses than another in the same warp would finish early and sit
idle while the other thread keeps working through its longer list,
wasting parallel capacity.

Sources:
[NVIDIA CUDA Programming Guide — Advanced Kernel Programming](https://docs.nvidia.com/cuda/cuda-programming-guide/03-advanced/advanced-kernel-programming.html),
[NVIDIA CUDA Programming Guide — Programming Model](https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/programming-model.html)

## Reservoir computing

A machine-learning framework for processing temporal/sequential data. A
large recurrent network, the "reservoir," is initialized once with random
weights and then left fixed; only a separate, much smaller linear readout
layer on top of it is trained. The reservoir's role is to project input
into a high-dimensional dynamic state that a simple readout can then learn
to read.

The **Liquid State Machine (LSM)** is the spiking-neural-network variant of
reservoir computing, introduced alongside the Echo State Network (ESN) in
the early 2000s. Both share the same core property: the reservoir's
internal weights are fixed after initialization, and only the readout is
trained.

Note: whether STDP applies to all synapses or only a subset is unsettled
and was still being prototyped/experimented with, not a stable design
fact.

Sources:
[Wikipedia — Reservoir computing](https://en.wikipedia.org/wiki/Reservoir_computing),
[ScienceDirect — Reservoir Computing overview](https://www.sciencedirect.com/topics/computer-science/reservoir-computing),
[Scholarpedia — Echo state network](http://www.scholarpedia.org/article/Echo_state_network)
