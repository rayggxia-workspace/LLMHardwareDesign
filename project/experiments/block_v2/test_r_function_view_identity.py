import copy
import json
from pathlib import Path
import tempfile
import unittest
from r_function_view_identity import identity,sha


class ViewIdentityTest(unittest.TestCase):
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
