"""Geometry regression fixtures, including shorts to PG and non-target pins."""
import argparse
import copy
import importlib.util
from pathlib import Path
import unittest

def load(name):
    spec=importlib.util.spec_from_file_location("hpy_test_"+name,Path(__file__).with_name(name+".py"))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
g=load("native_geometry");fx=load("test_native_inventory")

def fixture():
    data=fx.fixture()
    data["shapes"]=[r for r in data["shapes"] if not (r[0]=="WIRE_VIA" and r[1]=="in")]
    data["shapes"][0]=["BPIN","in","SIGNAL","p_in","metal1","ROUTING",70,202,80,206,"","",""]
    data["shapes"].append(["WIRE","in","SIGNAL","j1","metal1","ROUTING",80,202,104,206,"","",""])
    fx.recount(data);return data

class GeometryTests(unittest.TestCase):
    root=None
    def native(self,mutate=None):
        directory=self.root/self._testMethodName;directory.mkdir()
        data=fixture()
        if mutate:mutate(data)
        fx.recount(data);fx.write_tables(directory,data)
        return directory
    def test_complete_target_and_all_neighbor_index(self):
        result=g.analyze(self.native(),{"in"},10)
        self.assertEqual(result["status"],"pass_target_geometry")
        self.assertEqual(result["different_net_contacts"]["count"],0)
        self.assertEqual(result["nets"][0]["expected_endpoints"],2)
        self.assertGreater(result["counts"]["node_kinds"]["SPECIAL_VIA"],0)
        self.assertEqual(result["counts"]["unconnected_pin_net_ids"],1)
    def test_missing_route_is_open(self):
        result=g.analyze(self.native(lambda t:t["shapes"].pop()),{"in"},10)
        self.assertFalse(result["nets"][0]["passed"])
    def test_short_to_non_target_pin(self):
        def edit(t):t["shapes"][-1][8]=108
        result=g.analyze(self.native(edit),{"in"},10)
        self.assertEqual(result["status"],"fail_target_geometry")
        self.assertTrue(any(x["net_b"]=="out" for x in result["different_net_contacts"]["first_examples"]))
    def test_short_to_pg_conductor(self):
        def edit(t):t["shapes"].append(["SPECIAL_WIRE","VDD","POWER","pg","metal1","ROUTING",90,201,92,207,"","",""])
        result=g.analyze(self.native(edit),{"in"},10)
        self.assertTrue(any(x["net_b"]=="VDD" for x in result["different_net_contacts"]["first_examples"]))
    def test_short_to_unconnected_output_pin(self):
        def edit(t):t["shapes"][-1][8]=110
        result=g.analyze(self.native(edit),{"in"},10)
        self.assertTrue(any(x["net_b"].startswith("__HPY_UNCONNECTED__/") for x in result["different_net_contacts"]["first_examples"]))
    def test_unrelated_short_not_mislabeled_as_target_short(self):
        nodes=[g.make_node("m1",(0,0,1,1),"target","WIRE"),
               g.make_node("m1",(10,10,12,12),"b","WIRE"),
               g.make_node("m1",(11,11,13,13),"c","SPECIAL_WIRE")]
        self.assertEqual(g.target_contacts(nodes,{"target"},2)["count"],0)
    def test_corner_only_contact_does_not_connect(self):
        nodes=[g.make_node("m1",(0,0,1,1),"a","WIRE"),
               g.make_node("m1",(1,1,2,2),"a","WIRE")]
        self.assertEqual(len(set(g.geom.contact_graph(nodes,[]))),2)
    def test_corner_other_net_is_conservatively_reported(self):
        nodes=[g.make_node("m1",(0,0,1,1),"a","WIRE"),
               g.make_node("m1",(1,1,2,2),"b","WIRE")]
        self.assertEqual(g.target_contacts(nodes,{"a"},1)["count"],1)
    def test_other_layer_overlap_is_not_short(self):
        nodes=[g.make_node("m1",(0,0,3,3),"a","WIRE"),
               g.make_node("m2",(0,0,3,3),"b","WIRE")]
        self.assertEqual(g.target_contacts(nodes,{"a"},1)["count"],0)
    def test_cut_to_other_net_cut_is_checked(self):
        nodes=[g.make_node("v1",(0,0,3,3),"a","WIRE_VIA",layer_type="CUT"),
               g.make_node("v1",(1,1,2,2),"VDD","SPECIAL_VIA",layer_type="CUT")]
        self.assertEqual(g.target_contacts(nodes,{"a"},1)["count"],1)
    def test_comparison_budget_exhaustion_is_failure(self):
        nodes=[g.make_node("m1",(0,0,3,3),"a","WIRE"),
               g.make_node("m1",(1,1,2,2),"b","WIRE")]
        with self.assertRaisesRegex(RuntimeError,"incomplete"):
            g.target_contacts(nodes,{"a"},1,max_comparisons=0)
    def test_missing_pg_via_cut_rejected_before_contact_check(self):
        def edit(t):t["shapes"]=[r for r in t["shapes"] if not (r[0]=="SPECIAL_VIA" and r[5]=="CUT")]
        with self.assertRaisesRegex(ValueError,"Via boxes"):
            g.analyze(self.native(edit),{"in"},10)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--output",required=True);args=p.parse_args()
    GeometryTests.root=g.inv.safe_new(args.output)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GeometryTests))
    g.inv.write_json(GeometryTests.root/"result.json",{"tests":result.testsRun,"failures":len(result.failures),
          "errors":len(result.errors),"passed":result.wasSuccessful(),"scope":"Synthetic native geometry/contact fixtures"})
    return 0 if result.wasSuccessful() else 1
if __name__=="__main__":raise SystemExit(main())
