"""Known-unit parser controls, independent of an EDA acceptance verdict."""
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'project/experiments/control_v1'))
from native_cap_residual import inspect

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class NativeCapControls(unittest.TestCase):
    def fixture(self,root,bad_unit=False,missing=False,changed=False):
        def put(name,data):
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data));return p
        native=root/'native.spef';native.write_text('qualified-native-input')
        manifest=put('physical.json',{'leaves':{'one':{'final_files':{'6_final.spef':{'path':str(native),'sha256':sha(native)}}}}})
        graph=put('graph.json',{})
        spef=root/'joined.spef';spef.write_text('*C_UNIT 1 '+('FF'if bad_unit else'PF')+'\n*NAME_MAP\n*1 net_'+('8'if missing else'7')+'\n*D_NET *1 0.33\n*CAP\n1 *1:1 0.01\n2 *1:2 0.02\n3 *1:1 *1:2 0.3\n*RES\n1 *1:1 *1:2 1\n*END\n')
        put('sta/native-stitch.json',dict(passed=True,mode='native-access-plus-ideal-upper-diagnostic',inputs={str(native):sha(native)},output=str(spef),output_sha256=sha(spef)))
        put('sta/native-system-audit.json',{'passed':True})
        put('sta/receipt.json',dict(execution_passed=True,typed_native_timing_passed=True,inputs={str(manifest):sha(manifest),str(graph):sha(graph),str(spef):sha(spef)}))
        report=put('placement/wire-cap-lower-bound.json',dict(executed=True,research_model=True,rows=[dict(net='net_7',driver={'instance':'one'},physical_driver={'max_capacitance_ff':160},wire_capacitance_lower_bound_ff={'low':100,'base':130,'high':140})]))
        put('placement/receipt.json',dict(passed=True,outputs={report.name:sha(report)}))
        config=put('config.json',dict(native_sta=str(root/'sta'),placements=[str(root/'placement')]))
        if changed:spef.write_text(spef.read_text()+'\n')
        out=root/'out';out.mkdir();return config,manifest,graph,out

    def test_pf_ground_caps_and_conservative_coupling_omission(self):
        with tempfile.TemporaryDirectory()as d:
            args=self.fixture(Path(d));r=inspect(*args,{},sha);p=r['placements'][0];row=p['rows'][0]
            self.assertAlmostEqual(row['native_ground_cap_ff'],30)
            self.assertEqual(row['native_ground_entries'],2)
            self.assertEqual(p['violations'],{'low':0,'base':0,'high':1})
            self.assertFalse(r['whole_system_qualified'])

    def test_rejects_wrong_units_missing_net_and_changed_payload(self):
        for key in ['bad_unit','missing','changed']:
            with self.subTest(key=key),tempfile.TemporaryDirectory()as d:
                args=self.fixture(Path(d),**{key:True})
                with self.assertRaises(AssertionError):inspect(*args,{},sha)

if __name__=='__main__':unittest.main()
