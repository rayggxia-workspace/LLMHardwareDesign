"""Source interface and final-function dependency regression controls."""
from copy import deepcopy
from pathlib import PurePosixPath
import unittest

from audit import Invalid, audit_function_binding
from candidate_request import interface


class SourceInterfaceControls(unittest.TestCase):
    def test_bus_order_retained_for_both_directions(self):
        names, declarations, flat = interface("module t(clk,d,q); input clk;\n input [3:1] d;\n output [0:2] q;", "t")
        self.assertEqual(names, ["clk", "d", "q"])
        self.assertEqual(declarations["d"]["bits"], ["d[3]", "d[2]", "d[1]"])
        self.assertEqual(declarations["q"]["bits"], ["q[0]", "q[1]", "q[2]"])
        self.assertEqual(flat["d[2]"], "input")

    def test_unsupported_header_declaration_and_duplicates_rejected(self):
        for text in ("module t(input d,output q);", "module t(d); input wire d;",
                     "module t(d,d); input d;", "module t(d,q); input d;",
                     "module t(d); input d;\noutput d;", "module wrong(d); input d;"):
            with self.subTest(text=text), self.assertRaises(Invalid):
                interface(text, "t")


class FunctionBundle:
    """Narrow dependency fixture, not claimed native execution."""
    def __init__(self):
        self.index = {"top": "transaction6k", "policy": "A"}
        self.hashes = {"function_receipt": "1"*64, "function_report": "2"*64,
                       "source_receipt": "3"*64, "final_v": "4"*64}
        self.view = {"pipeline": "native_pipeline_escape.json", "final_function_control": {
            "path": "/function", "receipt_sha256": "1"*64, "proof_sha256": "2"*64}}
        scoreboard = {"passed": True, "seed": 1212026102, "transactions": 242, "cycles": 100, "assertions": 1000}
        self.proof = {"schema": "block-v1-native-final-function/1", "passed": True,
                      "top": "transaction6k", "policy": "A", "pipeline": self.view["pipeline"],
                      "source": "/source", "source_receipt_sha256": "3"*64,
                      "original_flow_netlist_sha256": "4"*64, "final_netlist_sha256": "5"*64,
                      "driver_sha256": "6"*64, "formal": {"passed": True, "checks": {"full": True},
                      "full_final_netlist_sha256": "4"*64, "physical_functional_view": {"full_view_sha256": "5"*64}},
                      "initial_state_runs": {name: {"initial_mode": mode, "runtime_seed": seed, "scoreboard": deepcopy(scoreboard)}
                                             for name, mode, seed in (("all-ones", 1, 121), ("random-121", 2, 121), ("random-122", 2, 122))}}
        self.receipt = {"passed": True, "inputs": {"project/experiments/block_v1/test_transaction.cpp": "6"*64}}

    def obj(self, role):
        return self.proof if role == "function_report" else self.receipt

    def digest(self, role):
        return self.hashes[role]

    def identity(self, role):
        return PurePosixPath("/source/receipt.json" if role == "source_receipt" else "/function/receipt.json")

    def owned(self, role, receipt, filename):
        if (role, receipt, filename) != ("function_report", "function_receipt", "native-final-function.json"):
            raise AssertionError("wrong ownership request")


class FunctionDependencyControls(unittest.TestCase):
    def test_same_source_proof_binding_without_replay_claim(self):
        b = FunctionBundle()
        result = audit_function_binding(b, b.view)
        self.assertTrue(result["verified"])
        self.assertIn("no independent functional replay", result["scope"])

    def test_changed_original_or_formal_netlist_rejected(self):
        for field in ("original_flow_netlist_sha256", "source_receipt_sha256"):
            b = FunctionBundle()
            b.proof[field] = "0"*64
            with self.subTest(field=field), self.assertRaises(Invalid):
                audit_function_binding(b, b.view)
        b = FunctionBundle()
        b.proof["formal"]["full_final_netlist_sha256"] = "0"*64
        with self.assertRaises(Invalid):
            audit_function_binding(b, b.view)

    def test_missing_state_failed_formal_and_wrong_seed_rejected(self):
        for mutate in (lambda b: b.proof["initial_state_runs"].pop("random-122"),
                       lambda b: b.proof["formal"]["checks"].update(full=False),
                       lambda b: b.proof["initial_state_runs"]["random-121"].update(runtime_seed=122),
                       lambda b: b.receipt["inputs"].clear(),
                       lambda b: b.proof["initial_state_runs"]["random-122"]["scoreboard"].update(assertions=999)):
            b = FunctionBundle()
            mutate(b)
            with self.assertRaises(Invalid):
                audit_function_binding(b, b.view)


if __name__ == "__main__":
    unittest.main()
