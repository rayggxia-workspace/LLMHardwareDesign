from pathlib import Path
import tempfile
import unittest
from r_monolithic_drc import compare_grid_only


class GridProofTest(unittest.TestCase):
    def test_actual_pinned_fixture_reports_and_exact_geometry(self):
        from r_complete_native_check import control_evidence
        import hashlib
        root=Path(__file__).resolve().parents[3]
        evidence,result=control_evidence(root,lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest())
        self.assertEqual(result['partition_fixture_results']['fragmented']['native_drc_count'],1)
        self.assertTrue(result['partition_fixture_results']['complete']['native_drc_zero'])
        self.assertIn('real_notch',(evidence/'spacing-negative-drc.rpt').read_text())

    def test_only_grid_changes_and_refuse_physical_or_coverage_changes(self):
        old=b'DESIGN example ;\nGCELLGRID X 0 DO 1052 STEP 5700 ;\nGCELLGRID Y 0 DO 1052 STEP 5700 ;\nNETS 1 ;\n- a + ROUTED metal2 ( 100 100 ) ( 200 * ) ;\nEND NETS\nEND DESIGN\n'
        new=old.replace(b'DO 1052 STEP 5700',b'DO 2 STEP 6000000')
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'before.def';b=Path(d)/'after.def';a.write_bytes(old);b.write_bytes(new)
            self.assertTrue(compare_grid_only(a,b)['identical_physical_geometry_and_connections'])
            for broken in (new.replace(b'( 200 * )',b'( 300 * )'),new.replace(b'6000000',b'5000000'),new+b'\n'):
                b.write_bytes(broken)
                with self.assertRaises(AssertionError):compare_grid_only(a,b)


if __name__=='__main__':unittest.main()
