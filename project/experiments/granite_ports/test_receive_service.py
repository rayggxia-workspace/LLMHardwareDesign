"""Synthetic tiny packed blocks; no real model arrays are used locally."""
import unittest
import numpy as np

from receive_service import array_sha, restore_blocks


class PackedCodeTests(unittest.TestCase):
    def test_explicit_block_address_geometry(self):
        original = np.arange(2*32*48, dtype=np.int64).astype(np.int8).reshape(2, 32, 48)
        packed = np.empty((2, 2, 3, 16, 16), np.int8)
        for e in range(2):
            for o in range(32):
                for k in range(48):
                    packed[e, o//16, k//16, k%16, o%16] = original[e, o, k]
        self.assertTrue(np.array_equal(restore_blocks(packed), original))
        corrupted = packed.copy()
        corrupted[1, 1, 2, 15, 15] ^= 1
        self.assertNotEqual(array_sha(corrupted), array_sha(packed))
        self.assertFalse(np.array_equal(restore_blocks(corrupted), original))

    def test_dtypes_and_layout_are_part_of_code_contract(self):
        with self.assertRaisesRegex(ValueError, "geometry"):
            restore_blocks(np.zeros((1, 1, 1, 16, 16), np.int16))
        with self.assertRaisesRegex(ValueError, "geometry"):
            restore_blocks(np.zeros((1, 1, 1, 8, 32), np.int8))


if __name__ == "__main__":
    unittest.main()
