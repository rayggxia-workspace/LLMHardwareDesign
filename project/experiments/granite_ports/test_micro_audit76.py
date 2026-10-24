"""Tiny independent micro-store and mathematical endpoint tests."""
import unittest

from micro_audit76 import byte_action, oracle, replay_lines


class IndependentMicroTests(unittest.TestCase):
    def test_signed_mul_and_carry_edges(self):
        self.assertEqual(byte_action(3, 128, 128, 0), (0, 64))
        self.assertEqual(byte_action(1, 255, 0, 1), (0, 1))
        self.assertEqual(byte_action(2, 0, 255, 1), (0, 1))
        self.assertEqual(oracle("mul_s32_u16", -3, 32768), {"value": -98304, "valid": True})

    def test_actual_dataflow_not_self_reported_operands(self):
        program = ["B tiny", "M 0 1 input_a", "I 0 255", "M 1 1 result", "M 2 1 flag",
                   "A 1 0 -2 -1 1 2 255 1 0 0 1", "E tiny"]
        result = replay_lines(program)[0]
        self.assertEqual(result["live_final"]["1"], 0)
        self.assertEqual(result["live_final"]["2"], 1)
        bad = program.copy()
        bad[-2] = "A 1 0 -2 -1 1 2 254 1 0 255 0"
        with self.assertRaisesRegex(ValueError, "live-store dependency"):
            replay_lines(bad)

    def test_no_host_injection_after_first_alu(self):
        program = ["B tiny", "M 0 2 input_a", "I 0 1", "A 0 0 -1 -1 1 -1 1 0 0 1 0", "I 1 99", "E tiny"]
        with self.assertRaisesRegex(ValueError, "injected intermediate"):
            replay_lines(program)

    def test_lifetime_and_uninitialized_reads(self):
        for program in (["B tiny", "M 511 2 input_a"],
                        ["B tiny", "M 0 1 input_a", "A 0 0 -1 -1 0 -1 0 0 0 0 0"],
                        ["B tiny", "M 0 1 input_a", "I 0 1", "F 0 1", "A 0 0 -1 -1 0 -1 1 0 0 1 0"]):
            with self.assertRaises(ValueError):
                replay_lines(program)

    def test_exact_oracle_signed_tie_and_rejection(self):
        self.assertEqual(oracle("rne_s64_i32", -5, shift=1), {"value": -2, "valid": True})
        self.assertEqual(oracle("add_s64", (1 << 63)-1, 1), {"value": -(1 << 63), "valid": False})
        self.assertEqual(oracle("abs_s64", -(1 << 63)), {"value": 1 << 63, "valid": True})
        self.assertEqual(oracle("div_rne_s128_u64_i32", -5, 2), {"value": -2, "valid": True})
        self.assertEqual(oracle("udiv_u128", 7, 0), {"valid": False})
        self.assertEqual(oracle("sub_s64", -(1 << 63), 1), {"value": (1 << 63)-1, "valid": False})
        self.assertEqual(oracle("max_s64", -(1 << 63), -1), {"value": -1, "valid": True})
        self.assertEqual(oracle("signextend_s16_i64", -32768), {"value": -32768, "valid": True})

    def test_published_output_must_read_actual_live_bytes(self):
        lines = ["B tiny", "M 0 2 input", "I 0 255", "I 1 1", "O value 1 0 255", "O valid 0 1 1", "E tiny"]
        result = replay_lines(lines)[0]
        self.assertEqual(result["outputs"], {"value": -1, "valid": True})
        self.assertEqual(result["result_read_bytes"], 2)
        lines[-3] = "O value 1 0 254"
        with self.assertRaisesRegex(ValueError, "causal live-store"):
            replay_lines(lines)


if __name__ == "__main__":
    unittest.main()
