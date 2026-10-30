"""
The spike ring buffer of the simulation (snn_simulation.cu: update(), _update_sim_pointers, update_current_),
transliterated to Python and replayed with synthetic spike counts (numpy only, no GPU). update_current_ must see
exactly the spikes of the last D steps (times t - D + 1 .. t) every step, also when the write pointer rewinds at
13 N spikes and under near-total activity. The transliteration follows the C++ statement by statement; a failure
here means the C++ logic fails in the same situation (confirm on the GPU with test_engine_probes.RingBuffer).

  PYTHONPATH=<repo root> python -m unittest discover -s snngine_v4/tests -p "test_ring_buffer.py" -v
"""

from __future__ import annotations

import unittest

import numpy as np


class RingBuffer:
    """SnnSimulation's spike bookkeeping (members as in snn_simulation.cuh, defaults included)."""

    def __init__(self, N: int, D: int, T: int, buffer_factor: int, threshold_factor=None):
        self.N, self.D = N, D
        # snn_simulation.cu: max(13, D) N; threshold_factor=13 reproduces the code before the fix
        tf = max(13, D) if threshold_factor is None else threshold_factor
        self.reset_firing_times_ptr_threshold = tf * N
        self.reset_firing_count_idx_threshold = 2 * T
        rows = max(buffer_factor, max(13, D) + 2)                    # Simulation: max(factor, max(13, D) + 2) rows
        self.counts = np.zeros(2 * T + 4, dtype=np.int64)          # Firing_counts (CSR row pointers, pairs)
        self.times = np.full(rows * N, -1, dtype=np.int64)         # Firing_times
        self.idcs = np.full(rows * N, -1, dtype=np.int64)          # Firing_idcs
        self.n_fired = self.n_fired_total = self.n_fired_total_m1 = 0
        self.n_fired_0 = self.n_fired_m1 = 0
        self.firing_counts_idx = self.firing_counts_idx_m1 = 1
        self.n_fired_m1_to_end = 0
        self.t = 0
        self.resetting = False
        self.write = 0                 # firing_times_write / firing_idcs_write (offset)
        self.read = 0                  # firing_times_read / firing_idcs_read (offset)
        self.counts_write = 0          # firing_counts_write (offset)

    def _update_sim_pointers(self):
        self.n_fired_0 = int(self.counts[self.firing_counts_idx])
        self.n_fired_total += self.n_fired_0
        self.n_fired += self.n_fired_0
        self.firing_counts_idx += 2
        if self.n_fired_total > self.n_fired_total_m1:
            self.n_fired_m1_to_end += self.n_fired_0
        if self.t >= self.D:
            self.n_fired_m1 = int(self.counts[self.firing_counts_idx_m1])
            self.n_fired_total_m1 += self.n_fired_m1
            self.n_fired -= self.n_fired_m1
            self.n_fired_m1_to_end -= self.n_fired_m1
            self.firing_counts_idx_m1 += 2
        if self.n_fired_total <= self.reset_firing_times_ptr_threshold:
            self.write += self.n_fired_0
        else:
            self.write = 0
            self.n_fired_total = 0
            self.resetting = True
        if self.firing_counts_idx > self.reset_firing_count_idx_threshold:
            self.firing_counts_idx = 1
            self.counts_write = 0
        else:
            self.counts_write += 2
        if self.firing_counts_idx_m1 > self.reset_firing_count_idx_threshold:
            self.firing_counts_idx_m1 = 1
        if self.n_fired_total_m1 <= self.reset_firing_times_ptr_threshold:
            self.read += self.n_fired_m1
        else:
            self.read = 0
            self.n_fired_m1_to_end = self.n_fired_total
            self.n_fired_total_m1 = 0
            self.resetting = False

    def step(self, fired_ids: np.ndarray):
        """One update(): the dense-to-sparse conversion writes this step's spikes (time t; t = 0 is not stored,
        fired[n] = t is 0 then) at the write pointers, the pointers move, update_current_ reads n_fired entries.
        Returns the (time, neuron) pairs update_current_ reads this step."""
        ids = np.asarray(fired_ids, dtype=np.int64) if self.t > 0 else np.zeros(0, np.int64)
        k = len(ids)
        if self.write + k > len(self.times):
            raise IndexError(f"write past the end of the spike buffer at t={self.t}")
        self.times[self.write:self.write + k] = self.t
        self.idcs[self.write:self.write + k] = ids
        self.counts[self.counts_write] = 0
        self.counts[self.counts_write + 1] = k
        self._update_sim_pointers()
        out = []
        for fired_idx in range(self.n_fired):
            if fired_idx < self.n_fired_m1_to_end:
                p = self.read + fired_idx
            else:
                p = fired_idx - self.n_fired_m1_to_end
            if not 0 <= p < len(self.times):
                raise IndexError(f"read outside the spike buffer at t={self.t} (position {p})")
            out.append((int(self.times[p]), int(self.idcs[p])))
        self.t += 1
        return out


def replay(N, D, counts_per_step, buffer_factor=40, T=10000, seed=0, threshold_factor=None):
    """Replay a sequence of spike counts; returns the first step where the reads differ from the ideal window, with
    the numbers missing and extra, or None."""
    rng = np.random.default_rng(seed)
    rb = RingBuffer(N, D, T, buffer_factor, threshold_factor)
    history = []
    for step, c in enumerate(counts_per_step):
        ids = np.sort(rng.choice(N, size=int(c), replace=False)) if c else np.zeros(0, np.int64)
        history.append((step, ids if step > 0 else np.zeros(0, np.int64)))
        try:
            got = rb.step(ids)
        except IndexError as e:
            return {"step": step, "error": str(e)}
        ideal = {(t, int(n)) for t, a in history[-D:] for n in a}
        got_set = set(got)
        if len(got) != len(got_set) or got_set != ideal:
            return {"step": step, "missing": len(ideal - got_set), "extra": len(got_set - ideal),
                    "duplicates": len(got) - len(got_set)}
    return None


class RingBufferLogic(unittest.TestCase):

    def test_low_activity(self):
        rng = np.random.default_rng(1)
        self.assertIsNone(replay(2000, 13, rng.integers(0, 40, 600)))

    def test_rewind_at_moderate_activity(self):
        """Several rewinds of the write pointer (13 N spikes) at 20 % of the neurons per step."""
        self.assertIsNone(replay(2000, 13, [400] * 600))

    def test_rewind_at_high_activity(self):
        """Near-total activity, as in a runaway: 90 % of the neurons fire every step."""
        self.assertIsNone(replay(2000, 13, [1800] * 200))

    def test_high_activity_d16(self):
        """D 16 (the 9 x 9 x 9 assembly networks): the write pointer rewinds after 13 N spikes; at 90 % of the neurons
        per step that takes fewer than D steps, so the new segment catches up with spikes still in the window."""
        self.assertIsNone(replay(2000, 16, [1800] * 200))

    def test_high_activity_d20(self):
        """D 20 (11 x 11 x 11): the same from about 13 / 19 = 68 % of the neurons per step."""
        self.assertIsNone(replay(2000, 20, [1500] * 200))

    def test_old_threshold_fails_at_d16(self):
        """Mutation check: the rewind after 13 N spikes (the code before the fix) loses spikes at D 16 and 90 %
        activity; the replay must detect it."""
        self.assertIsNotNone(replay(2000, 16, [1800] * 200, threshold_factor=13))

    def test_bursts(self):
        rng = np.random.default_rng(2)
        counts = np.where(rng.random(800) < 0.1, 1900, rng.integers(0, 50, 800))
        self.assertIsNone(replay(2000, 13, counts))

    def test_count_index_wrap(self):
        """The per-step count index wraps at 2 T (reset_firing_count_idx_threshold) while the trailing index lags D
        steps behind."""
        rng = np.random.default_rng(3)
        self.assertIsNone(replay(2000, 13, rng.integers(0, 200, 400), T=50))

    def test_engine_default_buffer(self):
        """The engine's own buffer size (15 N, Simulation's default) instead of the harness's 40 N, also at D 20."""
        self.assertIsNone(replay(2000, 13, [1500] * 200, buffer_factor=15))
        self.assertIsNone(replay(2000, 20, [1900] * 200, buffer_factor=15))


if __name__ == "__main__":
    unittest.main()
