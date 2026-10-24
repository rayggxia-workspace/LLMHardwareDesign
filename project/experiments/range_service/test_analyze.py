"""Analysis invariants without actual model/schedule execution."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("issue68_analysis_test", Path(__file__).with_name("analyze.py"))
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


def rows():
    answer = []
    for org, tile, route, ext in A.itertools.product(A.ORGS, A.TILES, A.ROUTES, A.EXTS):
        cycles = 100 + tile + (route == "spill") * 3 + ext
        if org != "shared8":
            cycles += 100
        answer.append({"organization": org, "tile": tile, "norm_route": route, "ext_ii": ext,
                       "task": "same", "task_fingerprint": "same", "state_bits": 32, "commit_contract": "same",
                       "best": {"cycles": cycles, "strategy": "fifo", "witness": org + str(tile) + route + str(ext),
                                "memory": {"R": 24576, **({"S4": 16384} if tile == 32 else {})},
                                "payload_bytes": 1000 + tile, "wire_bytes": 2000 + tile}})
    return answer


def tiny():
    banks = {"V": 16384, "R": 32768, **{"S" + str(i): 32768 for i in range(8)}}
    caps = {"BUS": 1, "SFU": 1, **{"PORT:" + b: 1 for b in banks}}
    nodes = []
    for i, (bank, stream) in enumerate((("V", "norm"), ("R", "R"))):
        nodes.append({"id": i, "kind": "work", "start": 0, "end": 5, "duration": 5, "deps": [],
                      "meta": {"stream": stream},
                      "reservations": [{"resource": "PORT:" + bank, "offset": 0, "duration": 5, "amount": 1}]})
    nodes.append({"id": 2, "kind": "finish", "start": 5, "end": 6, "duration": 1, "deps": [0, 1],
                  "meta": {}, "reservations": []})
    return {"nodes": nodes, "task": {"tokens": []}, "task_fingerprint": "synthetic", "makespan": 6,
            "config": {}, "inventory": {"capacities": caps, "bank_sizes": banks, "total_S8_lanes": 8, "active_contexts": 2},
            "allocations": [{"bank": "V", "offset": 0, "bytes": 16}, {"bank": "R", "offset": 0, "bytes": 16}],
            "producer_audit": {"resident_bytes": {"V": 16, "R": 16}}}


class AnalysisTest(unittest.TestCase):
    def test_union_and_parallel_durations_not_elapsed(self):
        self.assertEqual(A.union_length([(0, 5), (2, 8), (8, 9)]), 9)
        r = A.decompose(tiny())
        self.assertEqual(r["makespan"], 6)
        self.assertEqual(r["sum_node_duration_is_not_elapsed"], 11)
        self.assertEqual(r["precedence_lower_bound"], 6)
        self.assertEqual(r["resource_lower_bound"], 5)

    def test_paired_controls_and_issue_profiles(self):
        r = A.paired(rows())
        self.assertEqual(len(r["ranking56"]), 56)
        self.assertEqual(len(r["label_controls24"]), 24)
        self.assertEqual(len(r["tile_pairs28"]), 28)
        self.assertEqual({x["issue_profile"] for x in r["frontiers"]}, {"coarse8", "partitioned"})
        self.assertTrue(all(x["delta_cycles"] == 0 for x in r["label_controls24"]))
        r0 = rows()
        next(x for x in r0 if x["organization"] == "split4_4")["best"]["cycles"] += 1
        with self.assertRaisesRegex(ValueError, "label-only"):
            A.paired(r0)

    def test_incomparable_precision_rejected(self):
        r = rows()
        r[0]["state_bits"] = 16
        with self.assertRaisesRegex(ValueError, "incomparable"):
            A.paired(r)

    def test_clone_rescale_not_double_counted_as_failed_attempt(self):
        task = {"tokens": [{"attempts": [{"accepted": False}, {"accepted": True}]}]}
        for op, expected in (("clone_full_committed_trial", "R_full_trial_clone"),
                             ("full_head_trial_RNE_shift1", "R_rescale"),
                             ("outer_RNE_guard", "R_failed_attempt")):
            n = {"kind": "packet", "meta": {"stream": "R", "operation": op, "token": 0, "attempt": 0}}
            self.assertEqual(A.category(n, task), expected)

    def test_bank_alias_and_resource_overcommit_rejected(self):
        w = tiny()
        w["allocations"].append({"bank": "V", "offset": 8, "bytes": 16})
        with self.assertRaisesRegex(ValueError, "alias"):
            A.decompose(w)
        w = tiny()
        w["nodes"][1]["reservations"][0]["resource"] = "PORT:V"
        with self.assertRaisesRegex(ValueError, "overcommit"):
            A.decompose(w)

    def test_changed_arithmetic_budget_rejected(self):
        w = tiny()
        w["inventory"]["total_S8_lanes"] = 16
        with self.assertRaisesRegex(ValueError, "arithmetic"):
            A.decompose(w)


if __name__ == "__main__":
    unittest.main()
