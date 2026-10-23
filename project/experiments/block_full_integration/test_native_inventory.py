"""Small native-inventory negative fixtures; no EDA or external dependencies."""
import argparse
import collections
import csv
import gzip
import importlib.util
import json
from pathlib import Path
import unittest

_spec = importlib.util.spec_from_file_location("native_review",Path(__file__).with_name("native_review.py"))
rv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rv)

HEADERS = {
 "metadata":"key value",
 "layers":"name type routing_level",
 "masters":"master library master_type width height origin_x origin_y",
 "instances":"name master master_type x y origin_x origin_y orient status x0 y0 x1 y1",
 "master_geometry":"master category term io_type sig_type layer layer_type x0 y0 x1 y1",
 "iterms":"instance master term io_type sig_type net x0 y0 x1 y1",
 "bterms":"term io_type sig_type net pin_count",
 "nets":"net sig_type iterm_count bterm_count has_wire special_wire_count",
 "via_definitions":"scope name bottom_layer top_layer layer layer_type x0 y0 x1 y1",
 "shapes":"kind net sig_type object layer layer_type x0 y0 x1 y1 via via_x via_y",
 "shape_counts":"kind sig_type layer layer_type count",
 "virtual_connections":"net opcode junction_id from_junction"}

def write_tables(directory,tables):
    for name,header in HEADERS.items():
        with gzip.open(directory/(name+".tsv.gz"),"wt",encoding="utf-8",newline="") as f:
            writer = csv.writer(f,delimiter="\t",quoting=csv.QUOTE_NONE,lineterminator="\n")
            writer.writerow(header.split())
            writer.writerows(tables.get(name,[]))

def recount(tables):
    c = collections.Counter((r[0],r[2],r[4],r[5]) for r in tables["shapes"])
    tables["shape_counts"] = [[*key,n] for key,n in c.items()]

def fixture():
    terms = [("A","INPUT","SIGNAL","in",(1,2,4,6)),
             ("Z","OUTPUT","SIGNAL","out",(5,2,8,6)),
             ("U","OUTPUT","SIGNAL","",(9,2,10,6)),
             ("VDD","INOUT","POWER","VDD",(0,8,10,10))]
    t = {"metadata":[["block","fixture"],["dbu_per_um",1000],["manufacturing_grid_dbu",1],
          ["die_box","0 0 1000 1000"],["net_count",3],["instance_count",1],["unique_master_count",1],["complete","true"]],
         "layers":[["metal1","ROUTING",1],["metal8","ROUTING",8],["via8","CUT",0],["metal9","ROUTING",9],["metal10","ROUTING",10]],
         "masters":[["CELL","testlib","CORE",10,10,0,0]],
         "instances":[["u","CELL","CORE",100,200,100,200,"R0","PLACED",100,200,110,210]],
         "master_geometry":[],
         "iterms":[],
         "bterms":[["p_in","INPUT","SIGNAL","in",1],["p_out","OUTPUT","SIGNAL","out",1]],
         "nets":[["in","SIGNAL",1,1,1,0],["out","SIGNAL",1,1,1,0],["VDD","POWER",1,0,0,1]],
         "via_definitions":[],
         "shapes":[["BPIN","in","SIGNAL","p_in","metal9","ROUTING",100,200,110,210,"","",""],
                   ["BPIN","out","SIGNAL","p_out","metal9","ROUTING",120,200,130,210,"","",""],
                   ["BLOCK_OBS","","","obs","metal10","ROUTING",400,400,500,500,"","",""]],
         "virtual_connections":[]}
    for name,direction,sig,net,box in terms:
        t["master_geometry"].append(["CELL","PIN",name,direction,sig,"metal1","ROUTING",*box])
        t["iterms"].append(["u","CELL",name,direction,sig,net,box[0]+100,box[1]+200,box[2]+100,box[3]+200])
    t["master_geometry"].append(["CELL","OBS","","","","metal10","ROUTING",0,0,10,10])
    defs = [("metal8","ROUTING",(-2,-2,2,2)),("via8","CUT",(-1,-1,1,1)),("metal9","ROUTING",(-2,-2,2,2))]
    for layer,typ,box in defs:
        t["via_definitions"].append(["TECHNOLOGY","V8","metal8","metal9",layer,typ,*box])
    for kind,net,sig,obj,x,y in [("WIRE_VIA","in","SIGNAL","j1",100,200),("SPECIAL_VIA","VDD","POWER","s1",200,300)]:
        for layer,typ,box in defs:
            t["shapes"].append([kind,net,sig,obj,layer,typ,box[0]+x,box[1]+y,box[2]+x,box[3]+y,"V8",x,y])
    recount(t)
    return t

class NativeReviewTests(unittest.TestCase):
    root = None
    def make(self,mutate=None):
        d = self.root/self._testMethodName
        d.mkdir()
        t = fixture()
        if mutate:mutate(t)
        write_tables(d,t)
        return d
    def test_complete_fixture_and_unused_output(self):
        r = rv.review(self.make(),verify_hashes=False)
        self.assertEqual(r["unconnected_inputs"],0)
        self.assertEqual(r["unconnected_power_ground"],0)
        self.assertEqual(r["unconnected_iterms"][0]["count"],1)
        self.assertEqual(r["complete_via_instance_checks"],{"WIRE_VIA":1,"SPECIAL_VIA":1})
    def test_missing_connected_endpoint(self):
        with self.assertRaisesRegex(ValueError,"Missing/extra ITerm"):
            rv.review(self.make(lambda t:t["iterms"].pop(0)),verify_hashes=False)
    def test_missing_unused_endpoint(self):
        with self.assertRaisesRegex(ValueError,"Missing/extra ITerm"):
            rv.review(self.make(lambda t:t["iterms"].pop(2)),verify_hashes=False)
    def test_duplicate_endpoint_same_count(self):
        def mutate(t):t["iterms"][1]=t["iterms"][0][:]
        with self.assertRaisesRegex(ValueError,"Duplicate ITerm"):
            rv.review(self.make(mutate),verify_hashes=False)
    def test_wrong_signal_connection(self):
        def mutate(t):t["iterms"][0][5]="out"
        with self.assertRaisesRegex(ValueError,"Endpoint count mismatch"):
            rv.review(self.make(mutate),verify_hashes=False)
    def test_wrong_pin_transform(self):
        def mutate(t):t["instances"][0][7]="MX"
        with self.assertRaisesRegex(ValueError,"Transformed pin bbox mismatch"):
            rv.review(self.make(mutate),verify_hashes=False)
    def test_missing_pg_via_landing_even_with_recount(self):
        def mutate(t):t["shapes"].pop();recount(t)
        with self.assertRaisesRegex(ValueError,"Via boxes"):
            rv.review(self.make(mutate),verify_hashes=False)
    def test_moved_pg_via_landing(self):
        def mutate(t):t["shapes"][-1][6]+=1
        with self.assertRaisesRegex(ValueError,"Via boxes"):
            rv.review(self.make(mutate),verify_hashes=False)
    def test_missing_shape_with_original_counts(self):
        def mutate(t):t["shapes"].pop(2)
        with self.assertRaisesRegex(ValueError,"Missing/extra shape"):
            rv.review(self.make(mutate),verify_hashes=False)
    def test_missing_native_complete(self):
        def mutate(t):t["metadata"].pop()
        with self.assertRaisesRegex(ValueError,"Missing native complete"):
            rv.review(self.make(mutate),verify_hashes=False)
    def test_custom_layers_parameter_and_obs_separation(self):
        d = self.make()
        a = rv.inv.summarize(d,[9,10])
        b = rv.inv.summarize(d,[10])
        self.assertEqual(a["upper_layer_occupancy"]["electrical_geometry_boxes"],4)
        self.assertEqual(b["upper_layer_occupancy"]["electrical_geometry_boxes"],0)
        self.assertEqual(b["upper_layer_occupancy"]["custom_routing_levels"],[10])
    def test_all_eight_orientation_fixtures(self):
        expected={"R0":(101,202,104,206),"R90":(94,201,98,204),"R180":(96,194,99,198),
                  "R270":(102,196,106,199),"MX":(101,194,104,198),"MY":(96,202,99,206),
                  "MXR90":(102,201,106,204),"MYR90":(94,196,98,199)}
        for orient,box in expected.items():
            with self.subTest(orient=orient):
                self.assertEqual(rv.transform_box((1,2,4,6),(100,200),orient),box)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True)
    args = parser.parse_args()
    root = rv.inv.safe_new(args.output)
    NativeReviewTests.root = root
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(NativeReviewTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    rv.inv.write_json(root/"result.json",{"tests":result.testsRun,"failures":len(result.failures),
        "errors":len(result.errors),"passed":result.wasSuccessful(),
        "scope":"Synthetic table corruption/transform tests; no physical routing/signoff claim"})
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    raise SystemExit(main())
