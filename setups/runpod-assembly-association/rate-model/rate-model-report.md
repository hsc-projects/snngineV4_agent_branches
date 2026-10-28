# Rate Model for Assembly-Association Screening: Report

## 1. Summary of Preliminary Work (Substep 1)

Substep 1 ("Build the model and module checks") has been implemented and verified on the host CPU.

- **Zero-Dependency Implementation**: The model ([`rate_model.py`](file:///E:/dev/snngineV4_agent_branches/setups/runpod-assembly-association/rate-model/rate_model.py)) and test suite ([`test_rate_model.py`](file:///E:/dev/snngineV4_agent_branches/setups/runpod-assembly-association/rate-model/test_rate_model.py)) were built entirely within the Python standard library (`math`, `random`, `json`, `unittest`), leaving the host's existing Python installation untouched.
- **Topological & Coupling Match**: Distance-dependent connectivity follows $P(j \mid i) \propto \exp(-d(i, j) / \lambda)$ with $\lambda = 0.4$. The empirical connection ratio between nearest neighbors ($d=1$) and diagonal neighbors ($d=\sqrt{2}$) matches the theoretical target within 5% tolerance.
- **Chemical Diffusion Equivalence**: 7-point Laplacian operator with zero-flux boundary conditions matches `ChemicalField` in [`assoc_fields.py`](file:///E:/dev/snngineV4_agent_branches/setups/runpod-assembly-association/assoc_fields.py). Exact mass conservation under zero decay ($\Delta M = 0.000$) and geometric decay under positive decay factors were verified.
- **Assembly Group Bistability**: Location groups maintain quiescent baselines ($r_E < 0.05$) in the absence of stimulation, switch into active attractor states ($r_E > 0.5$) under transient current pulses ($I_{\text{inj}} = 2.0$), and sustain elevated activity ($r_E > 0.3$) through recurrent intra-group self-coupling.
- **Module Verification**: All 7 module test cases in `test_rate_model.py` pass (`Ran 7 tests ... OK`).
- **Runpod CPU Verification**: Successfully deployed and executed on Runpod CPU (`cpu3c`, 2 vCPUs, EU-RO-1, pod `oiynq4pyi0e5tp`). All 7 tests executed and passed in 2.275s with zero external package dependencies (`exit code 0`). The pod was immediately terminated upon completion (total run cost < $0.001).

---

## 2. Architecture & Formulation

### State Variables
For each of the $G = 343$ location groups ($7 \times 7 \times 7$ grid):
- $r_{E, g} \in [0, 1]$: Excitatory population firing rate ($\tau_E = 10\text{ ms}$).
- $r_{I, g} \in [0, 1]$: Inhibitory population firing rate ($\tau_I = 10\text{ ms}$).

### Rate Equations
$$\frac{dr_{E, g}}{dt} = \frac{-r_{E, g} + \sigma\left(\sum_j r_{E, j} (W_{EE, jg}^{\text{base}} + w_{jg}^{\text{fast}} + w_{jg}^{\text{perm}}) + I_{\text{inj}, g} - W_{IE, g} r_{I, g};\, \theta_E, \beta_E\right)}{\tau_E}$$

$$\frac{dr_{I, g}}{dt} = \frac{-r_{I, g} + \sigma\left(W_{EI, g} r_{E, g};\, \theta_I, \beta_I\right)}{\tau_I}$$

### Chemical Fields ($C_1, C_2$)
- Zero-flux 7-point Laplacian on a $7 \times 7 \times 7$ grid.
- Released in proportion to excitatory activity ($r_{E, g}$).
- $C_2$ gates the consolidation of $w^{\text{fast}}$ into $w^{\text{perm}}$ during short-circuit rounds.

---

## 3. Next Steps: Substep 2 (Admission Test)

1. Calibrate sigmoid parameters ($\theta_E, \beta_E$) and $\tau_E$ against the 12 pairs of seed 0 ($d=4$, reference s71 / E0).
2. Evaluate classification performance on seed 1 (12 pairs):
   - Measure Cohen's kappa ($\kappa \ge 0.4$) across {Contained Transfer, Ignition, Non-Transfer}.
3. Verify qualitative invariants:
   - Enlarged grid ($9 \times 9 \times 9$) eliminates ignitions and truncates reach.
   - Spatially uniform $C_2$ preserves associative outcomes.
