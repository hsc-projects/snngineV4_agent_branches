# References

Confirmed source material relevant to the project (distinct from
`agents/research-todos.md`, which is for *unverified* things to check).

## Nageswaran et al., 2009 — the foundational algorithm

Jayram Moorkanikara Nageswaran, Nikil Dutt, Jeffrey L. Krichmar, Alex
Nicolau, Alex Veidenbaum. "Efficient simulation of large-scale spiking
Neural networks using CUDA graphics processors." IJCNN 2009.
([ACM](https://dl.acm.org/doi/10.5555/1704555.1704736),
[IEEE](https://ieeexplore.ieee.org/document/5179043/),
[ResearchGate PDF](https://www.researchgate.net/publication/221534151_Efficient_simulation_of_large-scale_Spiking_Neural_Networks_using_CUDA_graphics_processors))

Confirmed by the user as the basic/foundational paper the project's CUDA
simulation code is based on — first implemented as a direct translation of
this paper, then progressively optimized (simplifications, matrix-operation
tricks) for further speed. Referenced in the codebase at
`snngine_v4/nn/NDKNV/`.

The same authors (Nageswaran, Dutt, Krichmar) went on to release
**CARLsim**, an open-source GPU-accelerated SNN simulation framework built
on this paper's foundation, still actively maintained
([UCI-CARL/CARLsim6 on GitHub](https://github.com/UCI-CARL/CARLsim6)).
Useful to cross-check or confirm algorithmic details against, if the paper
alone is unclear.

The original source code for this paper's GPU-SNN simulator was reportedly
released at `ics.uci.edu/~jmoorkan/project` (the paper's first author's
UCI page). Not verified as still live from this environment (network
access to that domain is blocked here); the user may provide it directly.

Rephrased abstract: describes an Izhikevich-neuron-based spiking neural
network (SNN) simulator running on a single GPU, as a low-cost, programmable
alternative to the clusters/supercomputers/dedicated hardware SNN
simulators traditionally required. On an NVIDIA GTX-280 (1 GB memory), the
GPU implementation was up to 26x faster than a CPU version for 100K neurons
with 50 million synaptic connections firing at ~7 Hz average rate, and only
~1.5x slower than real-time for 100K neurons with 10 million synaptic
connections.

Per the project's Workflow (`agents/common.md`), kernel-level detail from
this paper and its optimizations is deferred until the user provides
source material directly — this entry is a pointer, not a deep-dive.

## Izhikevich, 2003 — the neuron model

E.M. Izhikevich. "Simple model of spiking neurons." *IEEE Transactions on
Neural Networks*, 14(6), 2003.
([PDF](https://www.izhikevich.org/publications/spikes.pdf),
[PubMed](https://pubmed.ncbi.nlm.nih.gov/18244602/),
[ResearchGate](https://www.researchgate.net/publication/5606796_Simple_model_of_Spiking_Neurons))

The likely origin of the `a`, `b`, `c`, `d` neuron-state parameters
documented in SNNgine3D's Data model (`MultiModelNeuronStateTensor`) —
those are the standard parameter names from this model.

Rephrased abstract: proposes a neuron model that combines the biological
plausibility of Hodgkin-Huxley-type dynamics with the computational
efficiency of integrate-and-fire neurons — able to reproduce the spiking
and bursting behavior of known cortical neuron types while remaining cheap
enough to simulate tens of thousands of neurons in real time (1ms
resolution).

## [Provisional] Fidjeland & Shanahan — GPU SNN simulation (NeMo)

A. K. Fidjeland, M. Shanahan. "Accelerated Simulation of Spiking Neural
Networks Using GPUs." IJCNN 2010.
([PDF](https://www.doc.ic.ac.uk/~mpsha/IJCNN10b.pdf),
[ResearchGate](https://www.researchgate.net/publication/224181323_Accelerated_Simulation_of_Spiking_Neural_Networks_Using_GPUs))

Provisional — the user is fairly confident this is the second GPU-SNN
paper they had in mind (involving a CUDA feature around shared memory not
available at the time of the Nageswaran et al. paper), but it's
unconfirmed and the publication year (2010) doesn't exactly match the
user's recollection of 2008/2009. Presents "nemo," a platform for
simulating Izhikevich-model spiking neural networks on GPUs via CUDA,
aimed at real-time performance for embodied/robotics use.
