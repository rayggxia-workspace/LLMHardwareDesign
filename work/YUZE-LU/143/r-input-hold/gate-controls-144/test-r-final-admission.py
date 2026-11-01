"""Negative acceptance controls using actual failed/incomplete evidence."""
import hashlib,json,os
from pathlib import Path
import tempfile,unittest
from r_final_admission import native,diagnostic

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
ROOT=Path(os.environ.get('R_TEST_ROOT',str(Path(__file__).resolve().parents[3])))

class FinalAdmissionTest(unittest.TestCase):
    def test_actual_failed_producer_is_never_admitted(self):
        root=ROOT
        failed=root/'work/YUZE-LU/143/r-input-hold/final-126'
        self.assertFalse(json.loads((failed/'receipt.json').read_text())['passed'])
        with self.assertRaises(AssertionError):native(root,failed,failed,sha)

    def test_unfinished_producer_is_never_admitted(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            with self.assertRaises(FileNotFoundError):native(path,path,path,sha)

    def test_actual_successful_small_fixture_cannot_be_final_native(self):
        root=ROOT
        fixture=root/'work/YUZE-LU/143/r-input-hold/geometry-136'
        self.assertTrue(json.loads((fixture/'diagnostic.json').read_text())['diagnostic_completed'])
        with self.assertRaises(AssertionError):diagnostic(fixture,sha,'final-native')

    def test_actual_successful_rc_cannot_be_final_native(self):
        root=ROOT
        rc=root/'work/YUZE-LU/143/r-input-hold/geometry-137'
        self.assertTrue(json.loads((rc/'diagnostic.json').read_text())['fresh_rc_all_zero'])
        with self.assertRaises(AssertionError):diagnostic(rc,sha,'final-native')

    @unittest.skipIf(os.name=='nt','Linux EDA gate imports fcntl; run this control in pinned Slurm image')
    def test_function_join_cannot_accept_actual_failed_source(self):
        import qualify  # Sets the same module search paths as real gate CLI.
        from r_function_join import join
        root=ROOT
        failed=root/'work/YUZE-LU/143/r-input-hold/final-126'
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(AssertionError):join(root,failed,Path(d),None)

    @unittest.skipIf(os.name=='nt','Linux EDA gate imports fcntl; run this control in pinned Slurm image')
    def test_formal_join_cannot_accept_actual_failed_source(self):
        import qualify
        from r_formal_join import join
        root=ROOT
        failed=root/'work/YUZE-LU/143/r-input-hold/final-126'
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(AssertionError):join(root,failed,Path(d),None,None,None)

if __name__=='__main__':unittest.main()
