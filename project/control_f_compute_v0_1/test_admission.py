"""Static admission checks for the fixed F target."""
import unittest

from f_images import ADD, BYPASS, images, validate_pair, validate_sources


class Admission(unittest.TestCase):
    def test_g_and_ge(self):
        self.assertEqual(validate_pair(*images())["op"], BYPASS)
        self.assertEqual(validate_pair(*images(0, 1022, 1023, True))["op"], ADD)

    def test_source_blobs(self):
        validate_sources()

    def test_alias_and_reserved(self):
        for args in ((19, 0, 19, False), (1, 2, 2, True), (1, 3, 19, False),
                     (5, 0, 1024, False)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                validate_pair(*images(*args))

    def test_mutations(self):
        mother, local = images(2, 4, 19, True)
        # Mutations keep the binary shape and alter only one semantic field.
        fields = [(offset, 1) for offset in (64, 68, 84, 120, 141, 194, 242, 244, 296)]
        for offset, mask in fields + [(307, 64)]:
            changed = bytearray(local)
            changed[offset] ^= mask
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                validate_pair(mother, bytes(changed))
        with self.assertRaises(ValueError):
            validate_pair(mother[:-16], local)


if __name__ == "__main__":
    unittest.main()
