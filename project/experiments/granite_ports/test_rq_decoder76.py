"""Independent exact Fraction controls for the observed large-shift repair."""
from fractions import Fraction
import unittest

from audit_io76 import rational_rne
from rq_decoder76 import decode, rounded_s64, verify_alias


class ShiftDecoderTests(unittest.TestCase):
    def test_all_s64_extremes_large_shifts_have_exact_even_zero(self):
        for value in (-(1 << 63), -(1 << 63)+1, -1, 0, 1, (1 << 63)-1):
            for shift in (64, 65, 127, 128, 129, 130, 131, 32799):
                self.assertEqual(rational_rne(value, 1 << shift), 0)
                self.assertEqual(rounded_s64(value, shift), 0)
                self.assertEqual(verify_alias(value, shift, 0), min(shift, 128))
        self.assertEqual(Fraction(-(1 << 63), 1 << 64), Fraction(-1, 2))

    def test_boundary63_is_not_silently_zero(self):
        self.assertEqual(rounded_s64(-(1 << 63), 63), -1)
        self.assertEqual(rounded_s64((1 << 63)-1, 63), 1)
        self.assertEqual(verify_alias(-5, 1, -2), 1)
        with self.assertRaisesRegex(ValueError, "published integer code"):
            verify_alias((1 << 63)-1, 63, 0)

    def test_negative_and_non_s64_are_not_clamped(self):
        for value in (-1, -(1 << 63)):
            with self.assertRaisesRegex(ValueError, "negative RQ shift"):
                decode(value)
        with self.assertRaisesRegex(ValueError, "signed overflow"):
            decode(1 << 63)


if __name__ == "__main__": unittest.main()
