"""Independent geometry rejects real cut/grid/connectivity corruptions."""
import copy
import json
from pathlib import Path
import unittest
from pins import generate, verify, u

ROOT = Path(__file__).resolve().parents[3]
TECH = json.loads((ROOT / "project/experiments/block_v1/technology-2um-v1.json").read_text())


class Geometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan, cls.fixture, cls.proof = generate(dict(clk=dict(bits=1,direction="input"),
            data=dict(bits=96,direction="input"), result=dict(bits=64,direction="output")),400,TECH)

    def test_complete_inventory(self):
        self.assertTrue(self.proof["passed"])
        self.assertEqual(self.proof["connected_bits"],161)
        self.assertEqual(len({p["pin"] for p in self.plan["pins"]}),161)

    def test_unstaggering_is_not_a_rule_waiver(self):
        d=copy.deepcopy(self.fixture)
        chosen=[p for p in self.plan["pins"] if p["escape_side"]=="left"]
        x=min(p["xy_um"][0] for p in chosen)
        for p in chosen:
            delta=u(x-p["xy_um"][0])
            for shape in d["shapes"]:
                if shape["net"]==p["pin"]:
                    shape["box_dbu"][0]+=delta
                    shape["box_dbu"][2]+=delta
        with self.assertRaises(AssertionError):verify(d,TECH)

    def test_missing_via_rejected(self):
        d=copy.deepcopy(self.fixture)
        removed=next(s for s in d["shapes"] if s["layer"]=="via10")
        d["shapes"].remove(removed)
        with self.assertRaises(AssertionError):verify(d,TECH)

    def test_off_grid_cut_rejected(self):
        d=copy.deepcopy(self.fixture)
        cut=next(s for s in d["shapes"] if s["layer"]=="via10")
        cut["box_dbu"][0]+=1;cut["box_dbu"][2]+=1
        with self.assertRaises(AssertionError):verify(d,TECH)


if __name__=="__main__":unittest.main()
