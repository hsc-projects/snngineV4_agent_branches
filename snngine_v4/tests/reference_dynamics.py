"""
Independent numpy reference of the engine's per-step dynamics (snn_simulation.cu), for comparison with the engine
on small exported networks. Written from the kernel's stated semantics, not from the engine's Python code:

  update_N_state_ (Izhikevich branch, N_flags row 3 == 0), per neuron, float32:
      if v > 30: v = c, u += d, the neuron fires (its spike carries this step's time)
      v += 0.5 (0.04 v^2 + 5 v + 140 - u + i)      (twice)
      u += a (b v - u)
      then the input row is zeroed
  update_current_: every spike of the last D steps (time since firing k = 0 .. D - 1) adds the weights of its
      neuron's synapses in delay bucket k, [bnd[n, k], bnd[n, k + 1]), to their targets' input for the next step.

The engine sums with atomicAdd in float32, so its sums differ from this reference by rounding; compare with a
tolerance and only until the first step in which the spike sets differ.
"""

from __future__ import annotations

import numpy as np

F32 = np.float32


class ReferenceNetwork:

    def __init__(self, post, bnd, w, abcd, v0, u0):
        self.post = np.asarray(post, dtype=np.int64)          # (N, S)
        self.bnd = np.asarray(bnd, dtype=np.int64)            # (N, D + 1)
        self.w = np.asarray(w, dtype=F32)                     # (N, S)
        self.a, self.b, self.c, self.d = (np.asarray(abcd[:, j], dtype=F32).copy() for j in range(4))
        self.N, self.S = self.post.shape
        self.D = self.bnd.shape[1] - 1
        self.v = np.asarray(v0, dtype=F32).copy()
        self.u = np.asarray(u0, dtype=F32).copy()
        self.history = []                                      # fired ids of the last D steps, newest first

    def neuron_step(self, i: np.ndarray) -> np.ndarray:
        v, u = self.v, self.u
        fired = np.flatnonzero(v > F32(30.0))
        v[fired] = self.c[fired]
        u[fired] = u[fired] + self.d[fired]
        i = np.asarray(i, dtype=F32)
        for _ in range(2):
            v[:] = v + F32(0.5) * (F32(0.04) * v * v + F32(5.0) * v + F32(140.0) - u + i)
        u[:] = u + self.a * (self.b * v - u)
        return fired

    def deliver(self, fired: np.ndarray) -> np.ndarray:
        """Synaptic input for the next step, from the spikes of the last D steps (this step's included)."""
        self.history.insert(0, np.asarray(fired, dtype=np.int64))
        del self.history[self.D:]
        pre = np.concatenate(self.history)
        if len(pre) == 0:
            return np.zeros(self.N, dtype=F32)
        k = np.concatenate([np.full(len(a), j, dtype=np.int64) for j, a in enumerate(self.history)])
        lo = self.bnd[pre, k]
        cnt = self.bnd[pre, k + 1] - lo
        tot = int(cnt.sum())
        if tot == 0:
            return np.zeros(self.N, dtype=F32)
        # flat synapse indices pre * S + lo + 0 .. cnt - 1 of every (spike, bucket)
        start = pre * self.S + lo
        offs = np.cumsum(cnt) - cnt
        flat = np.repeat(start - offs, cnt) + np.arange(tot)
        out = np.bincount(self.post.reshape(-1)[flat], weights=self.w.reshape(-1)[flat], minlength=self.N)
        return out.astype(F32)

    def run(self, steps: int, inject_idx=(), inject_current: float = 0.0, inject_steps: int = 0):
        """The harness's stepping (assoc_protocol AssocRun.run without clamp, fields or plasticity): step, read the
        synaptic input, then add the injection for the next step. Returns the fired ids and synaptic inputs per step."""
        i = np.zeros(self.N, dtype=F32)
        fired_steps, inputs = [], []
        inject_idx = np.asarray(inject_idx, dtype=np.int64)
        for t in range(steps):
            fired = self.neuron_step(i)
            syn = self.deliver(fired)
            fired_steps.append(fired)
            inputs.append(syn.copy())
            i = syn
            if t < inject_steps and len(inject_idx):
                i = i.copy()
                i[inject_idx] += F32(inject_current)
        return fired_steps, np.stack(inputs)


def single_neuron_rate(a, b, c, d, current: float, steps: int = 1000, v0=-65.0) -> int:
    """Spikes of one isolated neuron under constant input, with the same update (for checking a single neuron)."""
    net = ReferenceNetwork(np.zeros((1, 1), np.int64), np.zeros((1, 2), np.int64), np.zeros((1, 1), F32),
                           np.array([[a, b, c, d]], F32), [v0], [F32(b) * F32(v0)])
    n = 0
    for _ in range(steps):
        n += len(net.neuron_step(np.array([current], F32)))
    return n
