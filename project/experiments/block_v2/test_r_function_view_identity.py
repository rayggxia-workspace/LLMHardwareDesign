import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'block_v1'))
from native_logic_projection import project
from r_function_view_identity import identity,sha


class ViewIdentityTest(unittest.TestCase):
    def test_rebuild_real_projection_and_refuse_nonpath_graph_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folders=[root/'143',root/'145']
            lib=root/'actual-control.lib'
            lib.write_text('library(control) {\n cell(ANTENNA_X1) {\n pin(A) {\n direction : input;\n capacitance : 0.01;\n }\n }\n }\n')
            graphs=[];proofs=[]
            for folder in folders:
                folder.mkdir();view=folder/'physical-functional.v';view.write_bytes(b'module projection_fixture; endmodule\n')
                graph={'modules':{'fixture':{'attributes':{'src':str(view)+':1.1-1.2'},'cells':{
                    'protection':{'type':'ANTENNA_X1','parameters':{},'port_directions':{'A':'input'},
                                  'connections':{'A':[2]},'attributes':{'src':str(view)+':2.1-2.2'}}}}}}
                _,projection=project(graph,lib.read_text())
                proof=dict(passed=True,full_view=str(view),full_view_sha256=sha(view),input_sha256={'actual.odb':'fixed'},
                           input_only_projection=projection,exact_other_signal_connectivity={'passed':True})
                (folder/'physical-functional.json').write_text(json.dumps(graph))
                (folder/'physical-functional-proof.json').write_text(json.dumps(proof))
                graphs.append(graph);proofs.append(proof)
            left=folders[0]/'physical-functional-proof.json';right=folders[1]/'physical-functional-proof.json'
            result=identity(left,right,sha(left),lib)
            self.assertTrue(result['exact_original_projection_reconstructed'])
            self.assertEqual(result['normalized_src_attributes'],2)
            for field in ('line','pin','metadata','digest'):
                changed=copy.deepcopy(graphs[1])
                entry=changed['modules']['fixture']['cells']['protection']
                if field=='line':entry['attributes']['src']=entry['attributes']['src'].replace(':2.1-2.2',':3.1-3.2')
                elif field=='pin':entry['connections']['A']=[3]
                elif field=='metadata':entry['attributes']['extra']='not a pathname'
                _,projection=project(changed,lib.read_text())
                if field=='digest':projection['original_graph_sha256']='wrong'
                proof=copy.deepcopy(proofs[1]);proof['input_only_projection']=projection
                (folders[1]/'physical-functional.json').write_text(json.dumps(changed))
                right.write_text(json.dumps(proof))
                with self.subTest(change=field),self.assertRaises(AssertionError):identity(left,right,sha(left),lib)

    def test_output_path_only_and_reject_graph_or_actual_bytes_change(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            left=root/'143';right=root/'145';left.mkdir();right.mkdir()
            for folder in (left,right):(folder/'physical-functional.v').write_bytes(b'module actual_export; endmodule\n')
            proof=dict(passed=True,full_view=str(left/'physical-functional.v'),
                       full_view_sha256=sha(left/'physical-functional.v'),input_sha256={'actual.odb':'fixed'},
                       input_only_projection={'original_graph_sha256':'graph'},exact_other_signal_connectivity={'passed':True})
            original=left/'physical-functional-proof.json';original.write_text(json.dumps(proof))
            chosen=right/'physical-functional-proof.json';selected=copy.deepcopy(proof);selected['full_view']=str(right/'physical-functional.v')
            chosen.write_text(json.dumps(selected));digest=sha(original)
            self.assertTrue(identity(original,chosen,digest)['passed'])
            selected['input_only_projection']['original_graph_sha256']='different'
            chosen.write_text(json.dumps(selected))
            with self.assertRaises(AssertionError):identity(original,chosen,digest)
            selected['input_only_projection']['original_graph_sha256']='graph';chosen.write_text(json.dumps(selected))
            (right/'physical-functional.v').write_bytes(b'changed actual export')
            with self.assertRaises(AssertionError):identity(original,chosen,digest)
            with self.assertRaises(AssertionError):identity(original,chosen,'wrong original proof hash')


if __name__=='__main__':unittest.main()
