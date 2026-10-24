"""Tiny independent physical-byte and fixed-wide-recipe checks only."""
import copy
import unittest

from receive_grouped_service import (BYTE_COST, WIDE_COST, engine_counts,
                                     expected_engines, recipe_inventory, verify_tree)


def operand(mode="read", stride=0):
    counts = engine_counts(15, 64, mode)
    bank = {"name": "bank.M", "start": 0 if mode == "read" else 6,
            "end": 5 if mode == "read" else 11}
    bus = {"name": "BUS", "start": 5 if mode == "read" else 0,
           "end": 11 if mode == "read" else 6}
    return {"kind": "engine_access", "start": 0, "end": 11, "engine": "VR8",
            "accesses": [{"object": "scratch", "offset": 0, "bytes": 64,
                          "mode": mode, "repeat": 1, "stride": 0,
                          "index_strides": [stride] if stride else []}],
            "counts": counts, "resources": [bank, bus] if mode == "read" else [bus, bank],
            "FIFO_peak_bytes": 96}


class GroupedPhysicalTests(unittest.TestCase):
    def test_independent_unaligned_read_write_packets(self):
        objects = {"scratch": {"offset": 15, "bytes": 128, "bank": "M"}}
        for mode in ("read", "write"):
            totals = verify_tree([operand(mode)], 11, objects, {"wide_factor": 1})
            self.assertEqual(totals["engine_local_beats"], 5)
            self.assertEqual(totals["wire_beats"], 6)
            self.assertEqual(totals["payload_bytes"], 64)
            self.assertEqual(totals["src_beats" if mode == "read" else "dst_beats"], 5)

    def test_affine_beat_classes_not_free_alignment(self):
        objects = {"scratch": {"offset": 15, "bytes": 128, "bank": "M"}}
        good = {"kind": "loop", "start": 0, "end": 22, "count": 2, "period": 11,
                "body": [operand(stride=16)]}
        totals = verify_tree([good], 22, objects, {"wide_factor": 1})
        self.assertEqual(totals["engine_local_beats"], 10)
        bad = copy.deepcopy(good)
        bad["body"][0]["accesses"][0]["index_strides"] = [1]
        with self.assertRaisesRegex(ValueError, "beat invariance"):
            verify_tree([bad], 22, objects, {"wide_factor": 1})

    def test_operand_bytes_cannot_be_forged_by_report(self):
        objects = {"scratch": {"offset": 15, "bytes": 128, "bank": "M"}}
        bad = operand()
        bad["accesses"][0]["bytes"] = 80
        with self.assertRaisesRegex(ValueError, "packet/bank"):
            verify_tree([bad], 11, objects, {"wide_factor": 1})

    def test_wide_costs_include_full_s32_signextend_and_i128_guard(self):
        self.assertEqual(WIDE_COST["signextend_i32_i64"], 11)
        self.assertEqual(WIDE_COST["alignment_shift64"], 18)
        self.assertEqual(WIDE_COST["rq_rne128_complete"], 182)
        counts = {"signextend_i32_i64": 16, "add64": 16}
        node = {"kind": "compute", "start": 0, "end": 42, "counts": counts,
                "resources": [{"name": "VR8", "start": 0, "end": 42}], "matrix_active_PEs": 16}
        self.assertEqual(verify_tree([node], 42, {}, {"wide_factor": 1})["add64"], 16)

    def test_whole_and_grouped_keep_one_final_product_operand_stream(self):
        whole = expected_engines("M", 1)
        grouped = expected_engines("V", 16)
        self.assertEqual(whole[0], ("local.m_acc", 0, 64, "read"))
        self.assertEqual(grouped[0], ("gs.V.partial", 0, 64, "read"))
        self.assertEqual(sum(name.endswith("product16") and mode == "write" for name, _, _, mode in whole), 25)
        self.assertEqual(sum(name.endswith("product16") and mode == "write" for name, _, _, mode in grouped), 45)
        self.assertEqual(sum(name.endswith("sum") and mode == "write" for name, _, _, mode in grouped), 16)


if __name__ == "__main__":
    unittest.main()
