from fractions import Fraction
import unittest

import numpy as np

import receive_numeric as receiver


class RouterReceiptTests(unittest.TestCase):
    def test_exact_scale_power_boundary_and_next_float(self):
        peak = 127 * 2.0 ** -10
        inputs = np.array([0, peak, np.nextafter(peak, np.inf), np.nextafter(peak, 0)])
        self.assertEqual(receiver.exact_exponent(inputs, 8).tolist(), [0, -10, -9, -10])
        self.assertEqual(receiver.exact_exponent(np.array([32767 * 2.0 ** -15]), 16).tolist(), [-15])

    def test_compile_encoding_rne_and_symmetric_saturation(self):
        x = np.array([[-3.5, -2.5, -0.5, 0.5, 2.5, 3.5, -128, 128]], np.float64)
        q, clip = receiver.encode(x, np.array([[0]], np.int16), 8)
        self.assertEqual(q.tolist(), [[-4, -2, 0, 0, 2, 4, -127, 127]])
        self.assertEqual(clip.tolist(), [[False] * 6 + [True, True]])

    def test_integer_equal_gate_is_exact_and_sum_preserved(self):
        logits = np.zeros((1, 40), np.int64)
        selected = np.arange(8, dtype=np.int16)[None]
        table = np.arange(2049, dtype=np.uint32)
        table[0] = 1 << 24
        gate, indices, clips = receiver.integer_gate(logits, np.array([0], np.int16), selected, table)
        self.assertEqual(gate.tolist(), [[4096] * 8])
        self.assertEqual(indices.tolist(), [[0] * 8])
        self.assertEqual(clips, 0)

    def test_integer_gate_clip_and_residual_ties(self):
        logits = -np.arange(40, dtype=np.int64)[None] * 100
        table = np.ones(2049, np.uint32)
        table[0] = 1 << 24
        gate, indices, clips = receiver.integer_gate(logits, np.array([0], np.int16), np.arange(8, dtype=np.int16)[None], table)
        self.assertEqual(clips, 7)
        self.assertEqual(indices.tolist(), [[0] + [2048] * 7])
        self.assertEqual(int(gate.sum()), 32768)

    def test_strict_certificate_refuses_ties_and_input_clip(self):
        aq = np.ones((2, 2), np.int8)
        wq = np.ones((40, 2), np.int8)
        logits = np.zeros((2, 40), np.int64)
        logits[:, :8] = 100
        ids = np.tile(np.arange(8, dtype=np.int16), (2, 1))
        clips = np.zeros((2, 2), np.bool_)
        clips[1, 0] = True
        cert, bound = receiver.certify(logits, ids, aq, wq, np.zeros(40, np.int16), clips)
        self.assertEqual(cert.tolist(), [True, False])
        logits[0, :8] = 6
        cert, bound = receiver.certify(logits, ids, aq, wq, np.zeros(40, np.int16), clips)
        self.assertEqual(cert.tolist(), [False, False])


if __name__ == "__main__":
    unittest.main()
