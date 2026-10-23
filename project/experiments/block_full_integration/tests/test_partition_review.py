#!/usr/bin/env python3
"""Small safety fixtures for partition cleanup proof; no DUT or EDA execution."""
import copy
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "partition.py"
spec = importlib.util.spec_from_file_location("partition_review_under_test", str(path))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CleanupProofSafety(unittest.TestCase):
    def ff(self):
        return {"type": "$dff", "parameters": {"WIDTH": "1", "CLK_POLARITY": "1"},
                "port_directions": {"D": "input", "CLK": "input", "Q": "output"},
                "connections": {"D": [2], "CLK": [3], "Q": [4]}}

    def design(self, ff, live=True):
        return {"ports": {"d": {"direction": "input", "bits": [2]},
                          "clk": {"direction": "input", "bits": [3]},
                          "q": {"direction": "output", "bits": [4 if live else 2]}},
                "cells": {"ff": ff}, "netnames": {}}

    def changed(self, before, after):
        return {"kind": "changed_state_or_memory", "module": "m", "cell": "ff",
                "before": before, "after": after}

    def check_change_rejected(self, after):
        before = self.ff()
        _, counts, _ = module.cleanup_attribution(
            {"m": self.design(before)}, {"m": self.design(after)},
            [self.changed(before, after)])
        self.assertEqual(counts, {"UNRESOLVED_STATE_EXPRESSION": 1})

    def test_clock_connection_change_rejected(self):
        after = self.ff()
        after["connections"]["CLK"] = ["0"]
        self.check_change_rejected(after)

    def test_clock_polarity_change_rejected(self):
        after = self.ff()
        after["parameters"]["CLK_POLARITY"] = "0"
        self.check_change_rejected(after)

    def test_live_state_deletion_rejected(self):
        before = self.ff()
        old = self.design(before)
        new = copy.deepcopy(old)
        new["cells"] = {}
        _, counts, _ = module.cleanup_attribution(
            {"m": old}, {"m": new},
            [{"kind": "removed_state_or_memory", "module": "m",
              "cell": "ff", "before": before}])
        self.assertEqual(counts, {"UNRESOLVED_OUTPUT_PATH": 1})

    def test_unobservable_state_is_explicitly_attributed(self):
        before = self.ff()
        old = self.design(before, live=False)
        new = copy.deepcopy(old)
        new["cells"] = {}
        _, counts, _ = module.cleanup_attribution(
            {"m": old}, {"m": new},
            [{"kind": "removed_state_or_memory", "module": "m",
              "cell": "ff", "before": before}])
        self.assertEqual(counts, {"NO_RAW_GRAPH_PATH_TO_MODULE_OUTPUT": 1})

    def arithmetic(self, typ, aw, yw, divisor, signed=0):
        cell = {"type": typ,
                "parameters": {"A_SIGNED": str(signed), "B_SIGNED": "0"},
                "port_directions": {"A": "input", "B": "input", "Y": "output"},
                "connections": {"A": list(range(2, 2+aw)),
                                "B": [str((divisor >> i) & 1) for i in range(32)],
                                "Y": list(range(100, 100+yw))}}
        m = {"ports": {"a": {"direction": "input", "bits": list(range(2, 2+aw))}},
             "cells": {"op": cell}}
        return module.local_expr_resolver(m, {"m": m})[0]

    def test_unsigned_divide_preserves_high_input_bits(self):
        get = self.arithmetic("$div", 32, 8, 256)
        for bit in range(8):
            self.assertEqual(get(100+bit), ("drivers", (), (("port", "a", bit+8),)))
        # Independent numeric counterexample: truncating A to Y before shifting
        # would incorrectly turn 0x0000ff00 / 256 into zero.
        self.assertEqual((0xff00 // 256) & 255, 255)
        self.assertNotEqual((0xff00 // 256) & 255, ((0xff00 & 255) // 256) & 255)

    def test_unsigned_divide_zero_extends_short_input(self):
        get = self.arithmetic("$div", 4, 8, 4)
        self.assertEqual(get(100), ("drivers", (), (("port", "a", 2),)))
        self.assertTrue(all(get(100+i) == ("constant", "0") for i in range(2, 8)))

    def test_non_power_of_two_not_rewritten(self):
        for typ in ("$div", "$mod"):
            get = self.arithmetic(typ, 32, 8, 3)
            self.assertEqual(get(100), ("drivers", (("op", typ, "Y", 0),), ()))

    def test_signed_division_not_rewritten_as_unsigned(self):
        get = self.arithmetic("$div", 32, 8, 256, signed=1)
        self.assertEqual(get(100), ("drivers", (("op", "$div", "Y", 0),), ()))


if __name__ == "__main__":
    unittest.main()
