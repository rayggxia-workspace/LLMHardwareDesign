import unittest

import codec
import compact


class CompactEncoding(unittest.TestCase):
    def test_every_opcode_at_min_and_max(self):
        for op in codec.OPS.values():
            role = "mother" if op["role"] == "both" else op["role"]
            for limit in ("min", "max"):
                instruction = {"op": op["name"]}
                for field in op["operands"]:
                    ceiling = compact.PC_MAX if op["name"] in compact.BRANCH_OPS and field["field"] in ("x", "y") else field[limit]
                    instruction[field["field"]] = min(field[limit], ceiling)
                with self.subTest(instruction=instruction):
                    self.assertEqual(compact.decode(compact.encode(instruction, role), role), instruction)

    def test_exact_branch_word_and_reserved_bits(self):
        instruction = dict(op="L_BRANCH", a=2, x=40, y=16)
        word = compact.encode(instruction, "local")
        self.assertEqual(word, 0x4b40002800100000)
        self.assertEqual(word.to_bytes(8, "little").hex(), "000010002800404b")
        for mask in (1, 1 << 48):
            with self.assertRaises(ValueError):
                compact.decode(word | mask, "local")
        with self.assertRaises(ValueError):
            compact.decode(word, "mother")
        with self.assertRaises(ValueError):
            compact.encode(dict(instruction, y=65536), "local")

    def test_program_targets_checked(self):
        with self.assertRaises(ValueError):
            compact.pack_program([dict(op="G_BRANCH", a=0, x=1, y=0), dict(op="G_END")], "mother", 2)
        with self.assertRaises(ValueError):
            compact.pack_program([dict(op="G_BRANCH", a=0, x=1, y=2), dict(op="G_END")], "mother", 2)

    def test_little_endian_lanes_and_odd_padding(self):
        program = [dict(op="G_MOVI", a=7, x=0xfedcba98), dict(op="G_WAIT", x=3), dict(op="G_END")]
        packed = compact.pack_program(program, "mother", 2)
        self.assertEqual(len(packed), 32)
        self.assertEqual(packed[:8].hex(), "98badcfe00000713")
        self.assertEqual(packed[24:], bytes(8))
        self.assertEqual(compact.unpack_program(packed, 3, "mother", 2), program)
        with self.assertRaises(ValueError):
            compact.unpack_program(packed[:-1]+b"\x01", 3, "mother", 2)
        with self.assertRaises(ValueError):
            compact.unpack_program(packed[:-1], 3, "mother", 2)


if __name__ == "__main__":
    unittest.main()
