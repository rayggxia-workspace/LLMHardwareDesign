"""Static U trial source and image admission checks."""
import unittest
from u_images import images, validate_pair, validate_sources


class Admission(unittest.TestCase):
    def test_valid(self):
        for args in ((), (0, 11, 1022, 1, 8, 1, -32768), (5, 6, 7, 8, 8, 0xffffffff, 32767)):
            self.assertEqual(len(validate_pair(*images(*args))["image_sha256"]), 2)

    def test_source_blobs(self):
        validate_sources()

    def test_reject_inputs(self):
        inputs = ((4,9,1023,8,5,1024,256), (4,21,20,8,5,1024,256), (4,4,20,8,5,1024,256),
                  (4,9,20,0,5,1024,256), (4,9,20,8,9,1024,256), (4,9,20,8,5,0,256),
                  (4,9,20,8,5,1024,32768), (4,9,20,8,5,0x100000000,0))
        for args in inputs:
            with self.subTest(args=args), self.assertRaises(ValueError):
                images(*args)

    def test_reject_mutations(self):
        mother, local = images()
        for pos, mask in ((64,1),(68,1),(84,1),(141,1),(194,1),(242,1),(244,1),(307,64),(309,1),(316,1)):
            changed = bytearray(local)
            changed[pos] ^= mask
            with self.subTest(pos=pos), self.assertRaises(ValueError):
                validate_pair(mother,bytes(changed))
        with self.assertRaises(ValueError):
            validate_pair(mother[:-16],local)


if __name__ == "__main__":
    unittest.main()
