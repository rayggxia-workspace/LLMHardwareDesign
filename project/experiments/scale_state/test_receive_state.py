"""Independent receiver boundaries; no producer import and no real-model run."""
import unittest
from fractions import Fraction
import numpy as np

from receive_state import (boundary_self_checks, rne, exact_bridge, integer_oracle,
                           calibration_units, bit_width)


class ReceiverTests(unittest.TestCase):
    def test_signed_rounding_and_stage_counterexamples(self):
        self.assertEqual(boundary_self_checks()["signed_RNE_Fraction_boundaries"], 144)
        for shift in range(1, 12):
            for n in range(-1024, 1025):
                self.assertEqual(rne(n, shift), round(Fraction(n, 1 << shift)))

    def test_exact_dyadic_bridge_ties_and_clipping(self):
        x = np.array([-9., -1.5, -.5, .5, 1.5, 9.])
        self.assertEqual(exact_bridge(x, 0, -2, 2).tolist(), [-2, -2, 0, 0, 2, 2])
        self.assertEqual(bit_width(-(1 << 62)), 63)
        self.assertEqual(bit_width(1 << 62), 64)

    def test_initial_calibration_only_units_and_floor(self):
        raw = {"calibration.initial_state": np.zeros((1, 2, 128, 128), np.float32),
               "calibration.final_state": np.zeros((1, 2, 128, 128), np.float32),
               "calibration.value": np.zeros((1, 32, 2, 128), np.float32)}
        raw["calibration.initial_state"][0, 1, 0, 0] = 4
        s, v = calibration_units(raw)
        self.assertEqual(s.tolist(), [-20, -11])
        self.assertEqual(v.tolist(), [-20, -20])

    def test_D31_exact_one_full_continuous_synthetic_path(self):
        q = np.zeros((32, 2, 128), np.int16)
        q[:, :, 0] = 2048
        k, v = np.zeros_like(q), np.zeros_like(q)
        beta = np.zeros((32, 2), np.uint16)
        decay = np.full((32, 2), 1 << 31, np.uint32)
        initial = np.full((2, 128, 128), 16, np.int32)
        wanted_states = np.full((33, 2, 128, 128), 16, np.int32)
        wanted_outputs = np.ones((32, 2, 128), np.int64)
        y, states, counts, maxima, widths = integer_oracle(
            q, k, v, beta, decay, initial, [0, 0], [0, 0], -(1 << 31), 32767 << 16,
            wanted_output=wanted_outputs, wanted_states=wanted_states, decay_fraction=31)
        self.assertEqual(counts["state_saturations"], 0)
        self.assertEqual(counts["output_Fraction_RNE"], 8192)
        self.assertEqual(maxima["decay_product"], 16 << 31)
        self.assertEqual(states.shape, (33, 2, 128, 128))


if __name__ == "__main__":
    unittest.main()
