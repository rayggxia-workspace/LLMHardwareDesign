"""Independent machine-word and byte-order vectors, rejection and control-flow checks."""
import json
import struct
import unittest
from pathlib import Path
import codec

class CodecTest(unittest.TestCase):
    def test_every_opcode_against_independent_struct_byte_layout(self):
        samples=dict(a=2,b=1,c=3,x=0x12345678,y=0x9abcdef0)
        for op in codec.SCHEMA["opcodes"]:
            instruction=dict(op=op["name"])
            for operand in op["operands"]:
                instruction[operand["field"]]=max(operand["min"],min(operand["max"],samples[operand["field"]]))
            role="mother" if op["role"]=="both" else op["role"]
            expected=struct.pack("<IIHBBBBBB",instruction.get("y",0),instruction.get("x",0),0,
                                 0,instruction.get("c",0),instruction.get("b",0),instruction.get("a",0),0,op["opcode"])
            actual=codec.encode_instruction(instruction,role).to_bytes(16,"little")
            self.assertEqual(actual,expected,op["name"])

    def test_full_uint64_parameter_address_is_preserved(self):
        record=dict(max_steps=1,parameter_base="0x0102030405060708")
        packed=codec.pack_record("task",record)
        self.assertEqual(packed[32:40],bytes.fromhex("0807060504030201"))
        self.assertEqual(codec.unpack_record("task",packed)["parameter_base"],0x0102030405060708)

    def test_independent_instruction_words_and_bytes(self):
        examples = json.loads((Path(__file__).parent / "examples.json").read_text())
        for v in examples["hand_vectors"]:
            with self.subTest(v=v):
                word = codec.encode_instruction(v["instruction"], v["role"])
                self.assertEqual(format(word, "032x"), v["word_hex"])
                if "bytes_le" in v:
                    self.assertEqual(word.to_bytes(16, "little").hex(), v["bytes_le"])
                self.assertEqual(codec.decode_instruction(word, v["role"]), v["instruction"])

    def test_reserved_bit_role_opcode_and_range_rejections(self):
        bad = [
            ({"op":"G_CALL","a":0,"b":32}, "mother"),
            ({"op":"L_EXEC","a":8}, "local"),
            ({"op":"L_EXEC","a":0,"b":8}, "local"),
            ({"op":"L_OPEN","a":16}, "local"),
            ({"op":"L_WAIT","x":0}, "local"),
            ({"op":"L_WAIT","x":256}, "local"),
            ({"op":"G_MOVI","a":8}, "mother"),
            ({"op":"G_MOVI","x":4294967296}, "mother"),
            ({"op":"G_MOVI","x":-1}, "mother"),
            ({"op":"G_MOVI","x":True}, "mother"),
            ({"op":"G_END","flags":1}, "mother"),
            ({"op":"G_END","imm":1}, "mother"),
            ({"op":"L_END","d":1}, "local"),
            ({"op":"G_CALL"}, "local"),
            ({"op":"L_EXEC"}, "mother"),
            ({"op":"L_END","extra":0}, "local"),
            ({"op":"UNKNOWN"}, "local"),
        ]
        for instruction, role in bad:
            with self.subTest(instruction=instruction):
                self.assertRaises(ValueError, codec.encode_instruction, instruction, role)
        for word in [0xff << 120, 1 << 128, -1, (0x4f << 120) | (1 << 80)]:
            self.assertRaises(ValueError, codec.decode_instruction, word, "local")

    def test_forward_branch_and_bounded_loop_encoding_domain(self):
        codec.check_program([{"op":"L_MOVI","a":0,"x":3},
                             {"op":"NOP"},{"op":"L_LOOP","a":0,"x":1},
                             {"op":"L_END"}], "local")
        codec.check_program([{"op":"G_BRANCH","a":0,"x":1,"y":2},
                             {"op":"G_FAIL","x":1},{"op":"G_END"}], "mother")
        cases = [
            [{"op":"L_LOOP","x":0},{"op":"L_END"}],
            [{"op":"L_BRANCH","x":0,"y":1},{"op":"L_END"}],
            [{"op":"L_BRANCH","x":1,"y":9},{"op":"L_END"}],
            [{"op":"NOP"}],
            [],
        ]
        for program in cases:
            self.assertRaises(ValueError, codec.check_program, program, "local")

    def test_independent_object_record_bytes_and_reserved_gap(self):
        obj = dict(object_id=2,kind=0,base_bytes=256,capacity_bytes=512,format=1,
                   object_version=7,length_bytes=128,native_abi_id=1)
        expected = bytes.fromhex(
            "01000200 00010000 00020000 00000000 01040000 07000000 ffff0000 80000000 01000000"
        ) + bytes(28)
        packed = codec.pack_record("object", obj)
        self.assertEqual(packed, expected)
        self.assertEqual(codec.unpack_record("object", packed)["base_bytes"],256)
        bad = bytearray(packed);bad[63]=1
        self.assertRaises(ValueError, codec.unpack_record, "object", bytes(bad))
        for change in [dict(version=2),dict(initial_valid_bytes=16),dict(flags=1),
                       dict(base_reg=8),dict(capacity_bytes=0),dict(unknown=0)]:
            self.assertRaises(ValueError, codec.pack_record,"object",dict(obj,**change))
        self.assertRaises(ValueError,codec.unpack_record,"object",packed[:-1])

    def test_record_layouts_are_nonoverlapping_and_fit(self):
        for name, record in codec.SCHEMA["records"].items():
            covered=set()
            for field in record["fields"]:
                self.assertEqual(field["bits"]%8,0)
                slots=set(range(field["offset"],field["offset"]+field["bits"]//8))
                self.assertFalse(covered & slots,name)
                covered |= slots
            self.assertLessEqual(max(covered)+1,record["bytes"],name)

    def test_schema_has_unique_codes_full_width_and_examples(self):
        codes=[o["opcode"]for o in codec.SCHEMA["opcodes"]]
        self.assertEqual(len(codes),len(set(codes)))
        bits=set()
        for field in codec.SCHEMA["fields"]:
            slots=set(range(field["lsb"],field["lsb"]+field["bits"]))
            self.assertFalse(bits & slots)
            bits |= slots
        self.assertEqual(bits,set(range(128)))
        output=codec.encode_examples()
        self.assertEqual(len(output["programs"]),2)
        for p in output["programs"]:
            self.assertEqual(len(bytes.fromhex(p["stream_bytes_le"])),16*len(p["instructions"]))
            for row in p["instructions"]:
                value=int(row["word_hex"],16)
                self.assertEqual(bytes.fromhex(row["bytes_le"]),value.to_bytes(16,"little"))

if __name__=="__main__":
    unittest.main()
