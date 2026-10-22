import unittest
import numpy as np
from numerical_oracles import (gqa_full, gqa_streaming, mla_expanded, mla_latent,
                               run_checks, swiglu_materialized, swiglu_tiled)


class NumericalOracleTests(unittest.TestCase):
    def test_deterministic_swiglu_known_value_and_tail(self):
        x = np.ones((1, 1), dtype=np.float64)
        w = np.ones((1, 7), dtype=np.float64)
        down = np.ones((7, 1), dtype=np.float64)
        expected = 7 / (1 + np.exp(-1))
        self.assertAlmostEqual(swiglu_materialized(x, w, w, down)[0, 0], expected)
        self.assertAlmostEqual(swiglu_tiled(x, w, w, down, hidden_tile=4)[0, 0], expected)

    def test_zero_scores_use_mean_of_permitted_values_and_contiguous_groups(self):
        q = np.zeros((3, 4, 1), dtype=np.float64)
        k = np.zeros((3, 2, 1), dtype=np.float64)
        v = np.array([[[1.], [10.]], [[3.], [30.]], [[5.], [50.]]])
        expected = np.array([[[1.], [1.], [10.], [10.]],
                             [[2.], [2.], [20.], [20.]],
                             [[3.], [3.], [30.], [30.]]])
        np.testing.assert_allclose(gqa_full(q, k, v), expected, rtol=1e-14, atol=1e-14)
        np.testing.assert_allclose(gqa_streaming(q, k, v, query_tile=2, key_tile=2), expected, rtol=1e-14, atol=1e-14)
        np.testing.assert_allclose(gqa_streaming(q[:1], k, v, query_offset=2), expected[-1:], rtol=1e-14, atol=1e-14)

    def test_very_large_logits_remain_finite_and_causal(self):
        q = np.full((1, 2, 3), 1000., dtype=np.float32)
        k = np.array([[[1000., 1000., 1000.]], [[-1000., -1000., -1000.]]], dtype=np.float32)
        v = np.array([[[7.]], [[99.]]], dtype=np.float32)
        for output in [gqa_full(q, k, v, query_offset=1), gqa_streaming(q, k, v, query_offset=1, key_tile=1)]:
            np.testing.assert_array_equal(output, np.full((1, 2, 1), 7., dtype=np.float32))

    def test_mla_one_key_has_known_projected_value_independent_of_scores(self):
        q = np.array([[[5., -7.]]])
        c = np.array([[2., 3., 4.]])
        wk = np.arange(6, dtype=np.float64).reshape(1, 3, 2)
        wv = np.array([[[1.], [2.], [3.]]])
        qr, kr = np.ones((1, 1, 2)), np.ones((1, 2))
        for output in [mla_expanded(q, c, wk, wv, qr, kr), mla_latent(q, c, wk, wv, qr, kr)]:
            np.testing.assert_array_equal(output, np.array([[[20.]]]))

    def test_invalid_offsets_grouping_tiles_and_nonfinite_are_rejected(self):
        q, k, v = np.ones((1, 4, 2)), np.ones((3, 2, 2)), np.ones((3, 2, 1))
        for offset in [-1, 3, 0.5, True]:
            with self.assertRaises(ValueError):
                gqa_streaming(q, k, v, query_offset=offset)
        with self.assertRaises(ValueError):
            gqa_full(np.ones((1, 3, 2)), k, v)
        with self.assertRaises(ValueError):
            gqa_streaming(q, k, v, key_tile=0)
        q[0, 0, 0] = np.nan
        with self.assertRaises(ValueError):
            gqa_full(q, k, v)

    def test_full_campaign_and_wrong_algebra_controls(self):
        result = run_checks()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["positive_checks"], 378)
        self.assertEqual(len(result["negative_controls"]), 3)
        self.assertTrue(all(case["detected"] for case in result["negative_controls"]))


if __name__ == "__main__":
    unittest.main()
