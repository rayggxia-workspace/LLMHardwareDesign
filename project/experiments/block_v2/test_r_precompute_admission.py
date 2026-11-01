import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from r_precompute_admission import evidence


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ComputationAdmissionTest(unittest.TestCase):
    def test_actual_fresh_rc_and_controls_allow_only_computation(self):
        root=Path(__file__).resolve().parents[3]
        result,report=evidence(root,sha)
        self.assertTrue(result['passed'] and result['computation_only'])
        self.assertFalse(result['qualified'] or result['native_leaf_accepted'])
        self.assertEqual(result['unresolved_native_drc_count'],822)
        self.assertEqual(report.count(b'violation type:'),822)

    def test_coherent_receipt_with_actual_hold_failure_is_refused(self):
        root=Path(__file__).resolve().parents[3]
        relative=Path('work/YUZE-LU/143/r-input-hold/geometry-137')
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/relative
            shutil.copytree(root/relative,target)
            diagnostic=target/'diagnostic.json'
            result=json.loads(diagnostic.read_text());result['fresh_rc_counts']['hold_checks']=1
            diagnostic.write_text(json.dumps(result))
            index=target/'index.json';data=json.loads(index.read_text())
            data['files']['diagnostic.json']=sha(diagnostic);index.write_text(json.dumps(data))
            with self.assertRaises(AssertionError):evidence(Path(temp),sha)


if __name__=='__main__':unittest.main()
