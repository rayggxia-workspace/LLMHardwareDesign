from fractions import Fraction
import unittest

import receive_outproj as receiver
from integer_oracle import shift_rne


class OutProjectionTests(unittest.TestCase):
    def test_signed_i128_physical_words_and_boundaries(self):
        for value in (-(1 << 127), -(1 << 80) - 5, -1, 0, 1, (1 << 127) - 1):
            high, low = value >> 64, value & ((1 << 64) - 1)
            self.assertEqual(receiver.reconstruct_i128(high, low), value)
        for high, low in (((1 << 63), 0), (0, -1), (0, 1 << 64)):
            with self.assertRaises(ValueError):
                receiver.reconstruct_i128(high, low)

    def test_one_final_rne_differs_from_rounding_each_partial(self):
        # 0.5 + 0.5 -> 1 once, but RNE(0.5)+RNE(0.5) -> 0.
        self.assertEqual(shift_rne(1 + 1, 1), 1)
        self.assertEqual(shift_rne(1, 1) + shift_rne(1, 1), 0)
        for value in (-(1 << 80) - 3, (1 << 80) + 3):
            self.assertEqual(shift_rne(value, 3), round(Fraction(value, 8)))

    def test_group_stream_wire_and_metadata_physical_rounding(self):
        self.assertEqual(receiver.wire_bytes(2), 48)
        self.assertEqual(receiver.wire_bytes(1984), 2016)
        self.assertEqual(receiver.wire_bytes(1985), 2064)
        self.assertEqual(receiver.wire_bytes(10240), 10432)
        # G1/G8/G16 exponent vectors fit a physical packet, but logical
        # metadata grows and must not be confused with beat-rounded wire.
        self.assertEqual([receiver.wire_bytes(g * 2) for g in (1, 8, 16)], [48, 48, 64])


if __name__ == "__main__":
    unittest.main()
