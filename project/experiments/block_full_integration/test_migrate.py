"""Regression fixtures for migration guards; no EDA or original data writes."""
import argparse
import copy
import importlib.util
from pathlib import Path
import unittest

def sibling(name):
    spec=importlib.util.spec_from_file_location("hpy_test_"+name,Path(__file__).with_name(name+".py"))
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
mig=sibling("migrate")
fx=sibling("test_native_inventory")

class MigrationTests(unittest.TestCase):
    root=None
    def pair(self,mutate):
        root=self.root/self._testMethodName;root.mkdir()
        before=root/"before";after=root/"after";before.mkdir();after.mkdir()
        original=fx.fixture()
        changed=copy.deepcopy(original);mutate(changed)
        fx.write_tables(before,original);fx.write_tables(after,changed)
        return before,after
    def test_unchanged_allowed(self):
        a,b=self.pair(lambda t:None)
        self.assertEqual(mig.compare(a,b,{"in"},False)["status"],"pass")
    def test_target_route_change_allowed(self):
        def edit(t):t["shapes"][3][6]+=1
        a,b=self.pair(edit)
        self.assertEqual(mig.compare(a,b,{"in"},True)["status"],"pass")
        self.assertEqual(mig.compare(a,b,{"in"},False)["status"],"fail")
    def test_non_target_route_change_rejected(self):
        def edit(t):t["shapes"][3][6]+=1
        a,b=self.pair(edit)
        self.assertEqual(mig.compare(a,b,{"out"},True)["status"],"fail")
    def test_target_pin_change_rejected(self):
        def edit(t):t["shapes"][0][6]+=1
        a,b=self.pair(edit)
        self.assertEqual(mig.compare(a,b,{"in"},True)["status"],"fail")
    def test_pg_change_rejected(self):
        def edit(t):t["shapes"][-1][6]+=1
        a,b=self.pair(edit)
        self.assertEqual(mig.compare(a,b,{"VDD"},True)["status"],"fail")
    def test_instance_move_rejected(self):
        def edit(t):t["instances"][0][3]+=1
        a,b=self.pair(edit)
        self.assertEqual(mig.compare(a,b,{"in"},True)["status"],"fail")
    def test_logical_connection_change_rejected(self):
        def edit(t):t["iterms"][0][5]="out"
        a,b=self.pair(edit)
        self.assertEqual(mig.compare(a,b,{"in"},True)["status"],"fail")
    def test_reserved_pin_or_pg_not_silently_selected(self):
        a,b=self.pair(lambda t:None)
        with self.assertRaisesRegex(ValueError,"PG/pin adapter"):
            mig.choose_targets(a,{9,10})
    def test_only_native_nets_section_retained(self):
        root=self.root/self._testMethodName;root.mkdir()
        source=root/"in.def";target=root/"out.def"
        body="    - data[0] ( U A ) + FIXED metal2 ( 1 2 ) ( 3 * ) ;\n"
        source.write_text('VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN sample ;\nUNITS DISTANCE MICRONS 2000 ;\nCOMPONENTS 1 ;\n- U CELL ;\nEND COMPONENTS\nNETS 1 ;\n'+body+"END NETS\nEND DESIGN\n")
        self.assertEqual(mig.nets_only_def(source,target),1)
        self.assertIn(body,target.read_text())
        self.assertNotIn("COMPONENTS",target.read_text())
        with self.assertRaises(FileExistsError):mig.nets_only_def(source,target)
    def test_malformed_nets_count_rejected(self):
        root=self.root/self._testMethodName;root.mkdir()
        source=root/"in.def"
        source.write_text('VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN sample ;\nUNITS DISTANCE MICRONS 2000 ;\nNETS 2 ;\n- n ;\nEND NETS\nEND DESIGN\n')
        with self.assertRaisesRegex(ValueError,"count mismatch"):
            mig.nets_only_def(source,root/"out.def")

    def prepare_reference(self):
        root=self.root/self._testMethodName;root.mkdir()
        (root/"import_fixed").mkdir();(root/"prepared_inventory").mkdir();(root/"prepared_inventory/native").mkdir()
        (root/"import_fixed/prepared.odb").write_bytes(b"fixture not an actual database")
        (root/"prepared_inventory/native/metadata.tsv.gz").write_bytes(b"fixture manifest only")
        mig.inv.write_json(root/"targets.json",{"nets":["a"],"custom_routing_levels":[9,10]})
        mig.inv.write_json(root/"prepare_comparison.json",{"status":"pass","forbidden_changes":[]})
        files=[p for p in root.rglob("*") if p.is_file()]
        mig.inv.write_json(root/"execution.json",{
          "status":"pass_fixed_encoding_qualification_only","case":"test",
          "tools":{"openroad":{"sha256":"tool"}},"inputs":{"odb":{"sha256":"source"}},
          "artifacts":{str(p.relative_to(root)):mig.inv.source_record(p) for p in files}})
        return root
    def test_prepared_evidence_reuse(self):
        root=self.prepare_reference()
        odb,proof=mig.qualified_reference(root,"test","source","tool",["a"],{9,10},"prepared")
        self.assertEqual(odb,root/"import_fixed/prepared.odb")
        self.assertTrue(proof["source_stages_reused"])
    def test_changed_prepared_odb_rejected(self):
        root=self.prepare_reference()
        (root/"import_fixed/prepared.odb").write_bytes(b"corruption")
        with self.assertRaisesRegex(ValueError,"evidence changed"):
            mig.qualified_reference(root,"test","source","tool",["a"],{9,10},"prepared")
    def test_other_source_or_tool_reuse_rejected(self):
        root=self.prepare_reference()
        for source,tool in [("other","tool"),("source","other")]:
            with self.subTest(source=source,tool=tool),self.assertRaisesRegex(ValueError,"another"):
                mig.qualified_reference(root,"test",source,tool,["a"],{9,10},"prepared")

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--output",required=True);args=p.parse_args()
    MigrationTests.root=mig.inv.safe_new(args.output)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MigrationTests))
    mig.inv.write_json(MigrationTests.root/"result.json",{"tests":result.testsRun,"failures":len(result.failures),
          "errors":len(result.errors),"passed":result.wasSuccessful(),"scope":"Synthetic migration guard fixtures"})
    return 0 if result.wasSuccessful() else 1
if __name__=="__main__":raise SystemExit(main())
