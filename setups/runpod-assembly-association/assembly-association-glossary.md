# Glossary: assembly association

Maps the terms of the assembly-association work (task files, report, tuning logs) to established
terms in the literature held in `archive/primary_literature/`. Each entry gives the established term
where one fits, its definition with the paper it is taken from, and how our usage differs.

**Rule:** use the established term where it means the same thing. Where it does not, or where no
term exists, keep our own term (marked **own**) and do not bend the idea to fit existing vocabulary;
the approach is partly new (no complete prior art for questions D1 and D3 of the literature
searches; see the ranking in `archive/unsorted_literature/`). Mark terms
whose fit is partial as **partial**.

## Network and substrate

- **Assembly** → *cell assembly* (partial). A group of neurons more strongly connected to each other
  than to the rest, which tends to be active together (Miehl et al. 2023, review). Ours is imposed by
  position: a location group with boosted intra-group input ("shortcut 1", own), not formed by
  learning.
- **Location group** (own). The neurons at one cell of the engine's cubic grid; the unit of the
  chemical fields and of activity measures.
- **Ordinary neuron** (own). A neuron outside every assembly. Hiratani et al. 2013 call neurons
  outside the retrieved pattern "background (BG) neurons", and Lehr et al. 2022 call non-assembly
  neurons recruited by learning "support neurons"; we keep "ordinary" because "background" is
  already used for background input.
- **Distance-dependent rewiring, lambda** (partial). Connection probability falling with distance,
  exp(-d / lambda), lambda in grid cells; the general notion is a spatially dependent connection
  probability with a length constant.
- **Heavy-tailed / lognormal weights; strong-sparse and weak-dense (SSWD)**. Most synapses weak, a
  few strong; in SSWD networks strong synapses transmit only on top of the depolarization supplied
  by the many weak ones (Teramae et al. 2012; Teramae & Fukai 2014; Hiratani et al. 2013).
- **Suprathreshold synapse; single-synapse threshold** → *autocrat connection* (Kuśmierz et al.
  2020): a connection with J_ij > theta, able to fire its target alone. The single-synapse threshold
  (own) is the smallest normalized weight that does so in our network; `lam_sup` (own) is the mean
  number of autocrat connections per neuron, the branching parameter of Kuśmierz et al. 2020.
- **All-or-none propagation** → *discontinuous transition with hysteresis* (Kuśmierz et al. 2020,
  for Gaussian weights and many inputs per neuron); **graded propagation** → *continuous
  transition*, critical at a mean of one autocrat connection per neuron (heavy-tailed weights).

## Plasticity

- **`w_fast` / `w_perm`** → *early-phase / late-phase weight* (partial; Clopath et al. 2008; Lehr et
  al. 2022). Early-phase changes decay unless consolidated into the late phase. Our `w_fast` decays
  with a fixed time constant and is moved into `w_perm` by the C2 gate, without tags in the
  predecessor.
- **Consolidation** → *synaptic consolidation* (Clopath et al. 2008; Ziegler et al. 2015): the
  conversion of early-phase into late-phase change.
- **Tag, protein, capture** → *synaptic tagging and capture (STC)* (Clopath et al. 2008; Luboeinski &
  Tetzlaff 2021; Lehr et al. 2022): a synapse is tagged when its early-phase change exceeds a
  threshold; plasticity-related proteins made by the neuron are captured by tagged synapses, which
  then consolidate. In Lehr et al. 2022 protein synthesis starts when the neuron's summed early-phase
  change exceeds a threshold that falls with the neuromodulator level.
- **`pre_c1`** (own name) → *non-local learning* gated by a *diffusing messenger* (partial; Krekelberg
  & Taylor 1997): weight change set by presynaptic activity and the local messenger concentration,
  with no postsynaptic term. Their rule also depresses at low presynaptic rates (variant L3); `pre_c1`
  only potentiates.
- **BTSP-like rule, gate event** → *behavioral time scale synaptic plasticity (BTSP)*; *plateau
  potential*; *eligibility trace*; *instructive signal* (Bittner et al. 2017; Milstein et al. 2021;
  Cone & Shouval 2021). Presynaptic activity leaves an eligibility trace lasting seconds; a dendritic
  plateau potential produces an instructive signal; their overlap changes the weight, with no
  postsynaptic action potential needed. Our "gate event" is the plateau, or C1 above a threshold
  (variant L2, own).
- **Heterosynaptic plasticity** (Chistiakova et al. 2015): changes at synapses that were not active
  during induction, triggered by strong postsynaptic activity. **Summed-weight limit** →
  *heterosynaptic competition* (Fiete et al. 2010).
- **Heterosynaptic cooperation and competition** (Nunes et al. 2024; terms of the tagging-and-capture
  literature): two weakly potentiated inputs to the same neurons are both maintained, though neither
  is alone (cooperation); a third potentiated input makes all of them decay, a strongly potentiated
  one included (competition). Nunes et al. read competition as active destabilization, not division of
  a limited protein pool. Variant K7 uses it as a band on a neuron's summed change.
- **Silent synapse** (Wang et al. 2018): a synapse with NMDA receptors but no AMPA receptors, which
  transmits only while the postsynaptic neuron is depolarized (responses at -35 mV, none at -70 mV);
  *unsilencing*: learning makes it transmit at rest. Ours (variant S5, partial): a voltage-dependent factor on
  the transmission of point-neuron synapses, set through the per-synapse gain; no receptor types.
- **Subtractive / multiplicative normalization** (Miller & MacKay 1994): keeping a neuron's summed
  weight constant by subtracting an equal amount from each weight, or by scaling all weights by one
  factor. Under subtractive normalization weights are driven to their bounds, so some win and others
  are eliminated; under multiplicative normalization they keep graded values. A shared receptor pool
  gives multiplicative scaling (Triesch et al. 2018).

## Chemicals and energy

- **C1** (own). A field released depending on activity that gates the induction of plastic
  changes; in the sparse task the long-range "bridge" that reaches neurons that do not fire. Closest: the *diffusing messenger* of non-local learning (Krekelberg & Taylor 1997) and
  NO in Gally et al. 1990.
- **C2** (own). A field released depending on activity that gates consolidation; in the sparse
  task the short-range "marker". Closest: the
  *neuromodulator* of Lehr et al. 2022, but there a global scalar; a spatially diffusing
  consolidation signal has no established term (prior-art question D3).
- **C3, fuel** (own). A resource with a fixed global supply, delivered where it was used. Closest:
  the *resource consumption principle* (Montague 1996, conceptual), and blood supply in
  neurovascular coupling (Devor et al. 2007; Boas et al. 2008).
- **Stringency** (Montague 1996): how strictly synapses must match to consume the shared resource,
  set by a temperature-like signal T; lowering T raises it; NO is proposed as a candidate for T. Our
  variant K1 (falling C2 level) applies the idea to consolidation.
- **Stigmergy** (concept term, from the user's inspiration). A trace left in the medium that guides
  later activity; Chialvo & Millonas 1995 apply it to ant swarms and draw only an analogy to neural
  maps (prior-art question D2).

## Protocol and measures (all own)

- **Joint round:** A and B injected together (co-activation), then a test with A alone.
- **Transfer:** in that test, A alone activates B (activity >= 0.5) on `w_fast`; a recall during
  training. **Final test:** recall on `w_perm` after training.
- **Ignition:** a transfer whose spread exceeds the stray limit, typically over much of the
  reservoir.
- **Short circuit stage** (concept term): joint rounds in which C2 moves `w_fast` into `w_perm`.
- **Route, strays, bridge assemblies, stray limit, `R_off`, M / Sh regions:** defined in the sparse
  task's "Terms" and in the predecessor report.
- **Controls:** control 0, control 1, joint-activation control, uniform-C2 control; defined in the
  sparse task's "Terms".
