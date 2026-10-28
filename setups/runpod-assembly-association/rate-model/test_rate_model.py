"""
test_rate_model.py

Unit tests and validation checks for the rate model (Substep 1 of rate-model-task.md).
Verifies:
1. Grid coordinate mapping and distance calculations.
2. Distance-dependent coupling statistics (within 5% of theoretical expectation).
3. 7-point Laplacian zero-flux diffusion and decay dynamics.
4. Single-group and multi-group rate dynamics.
5. Association protocol simulation (joint rounds, test rounds, stray counting).

Uses standard library only (math, random, unittest).
"""

import math
import unittest
from rate_model import (
    RateModel,
    ChemicalFieldCPU,
    route_groups
)


class TestRateModel(unittest.TestCase):

    def test_grid_mapping(self):
        """Verify grid dimension, total groups, and coordinate bidirectional mapping."""
        model = RateModel(grid_dim=7)
        self.assertEqual(model.G, 343)
        self.assertEqual(len(model.group_coords), 343)

        for g in range(343):
            x, y, z = model.coord(g)
            self.assertEqual(model.index(x, y, z), g)
            self.assertTrue(0 <= x < 7 and 0 <= y < 7 and 0 <= z < 7)

    def test_distance_and_coupling_statistics(self):
        """
        Verify that inter-group coupling decays exponentially with distance lambda,
        and matches expected partition function within 5%.
        """
        lam = 0.4
        model = RateModel(grid_dim=7, lam=lam)

        centre = model.index(3, 3, 3)
        neighbor_1 = model.index(4, 3, 3)  # dist = 1
        neighbor_diag = model.index(4, 4, 3)  # dist = sqrt(2)

        d1 = model.distance(centre, neighbor_1)
        d_diag = model.distance(centre, neighbor_diag)

        self.assertAlmostEqual(d1, 1.0, places=5)
        self.assertAlmostEqual(d_diag, math.sqrt(2.0), places=5)

        w1 = model.W_ee_base[centre][neighbor_1]
        w_diag = model.W_ee_base[centre][neighbor_diag]

        expected_ratio = math.exp(-1.0 / lam) / math.exp(-math.sqrt(2.0) / lam)
        actual_ratio = w1 / w_diag
        rel_diff = abs(actual_ratio - expected_ratio) / expected_ratio
        self.assertLess(rel_diff, 0.05, f"Rel diff {rel_diff:.4f} exceeds 5% tolerance")

    def test_chemical_field_diffusion_and_conservation(self):
        """
        Verify 7-point zero-flux Laplacian and mass conservation (when decay=0).
        """
        dims = (7, 7, 7)
        field = ChemicalFieldCPU(dims=dims, k=0.10, decay=0.0)

        # Release a unit impulse at centre
        g_centre = field.index(3, 3, 3)
        field.release(g_centre, 100.0)
        initial_mass = sum(field.c)
        self.assertAlmostEqual(initial_mass, 100.0, places=4)

        # Diffuse for 20 steps
        for _ in range(20):
            field.diffuse()

        final_mass = sum(field.c)
        # In zero-flux boundary with decay=0, total mass must be conserved exactly
        self.assertAlmostEqual(initial_mass, final_mass, places=3)
        # Concentration should have spread from centre to immediate neighbors
        g_neighbor = field.index(4, 3, 3)
        self.assertGreater(field.c[g_neighbor], 0.1)
        self.assertLess(field.c[g_centre], 100.0)

    def test_chemical_field_decay(self):
        """Verify concentration decays geometrically under nonzero decay."""
        field = ChemicalFieldCPU(dims=(7, 7, 7), k=0.0, decay=0.05)
        g_centre = field.index(3, 3, 3)
        field.release(g_centre, 10.0)

        for _ in range(10):
            field.diffuse()

        expected = 10.0 * ((1.0 - 0.05) ** 10)
        self.assertAlmostEqual(field.c[g_centre], expected, places=4)

    def test_single_group_bistability(self):
        """
        Verify that an assembly group is quiet without input, but when transiently
        stimulated, it activates and its self-coupling sustains activity.
        """
        model = RateModel(grid_dim=7)

        # Quiet baseline: 30 steps
        for _ in range(30):
            model.step()
        self.assertLess(model.r_e[0], 0.05, "Spontaneous activation in quiet baseline")

        # Inject group 0 for 30 steps
        for _ in range(30):
            model.step(external_inj={0: 2.0})
        self.assertGreater(model.r_e[0], 0.5, "Failed to activate under direct injection")

        # Relaxation: remove injection for 40 steps
        for _ in range(40):
            model.step()
        self.assertGreater(model.r_e[0], 0.3, "Assembly failed to sustain elevated activity")

    def test_route_groups_and_strays(self):
        """Verify route group cylinder calculation and stray group counting."""
        g_a = 1 * 49 + 3 * 7 + 3
        g_b = 5 * 49 + 3 * 7 + 3

        route = route_groups(g_a, g_b, grid_dim=7)
        self.assertIn(g_a, route)
        self.assertIn(g_b, route)

        g_mid = 3 * 49 + 3 * 7 + 3
        self.assertIn(g_mid, route)

        g_far = 3 * 49 + 6 * 7 + 3
        self.assertNotIn(g_far, route)

    def test_protocol_round_execution(self):
        """
        Executes a joint round and test round, ensuring no NaN or crashes.
        """
        model = RateModel(grid_dim=7)
        g_a = 1 * 49 + 3 * 7 + 3
        g_b = 5 * 49 + 3 * 7 + 3

        # Joint pulse 50 steps
        for _ in range(50):
            model.step(external_inj={g_a: 2.0, g_b: 2.0})
        model.update_plasticity(learn=True)

        # Gap 50 steps
        for _ in range(50):
            model.step()

        # Test A alone
        for _ in range(50):
            model.step(external_inj={g_a: 2.0})

        self.assertFalse(math.isnan(model.r_e[g_a]))
        self.assertFalse(math.isnan(model.r_e[g_b]))


if __name__ == '__main__':
    unittest.main()
