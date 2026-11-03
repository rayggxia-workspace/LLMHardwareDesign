"""An actual zero-passive inventory must retain every strict timing gate."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'block_v1'))
from pg_fixed_timing import inspect_timing

class EmptyPassiveTest(unittest.TestCase):
    def run_case(self,slacks,setup_count=0):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp)
            (root/'endpoints.tsv').write_text('real/D\t'+slacks+'\t0\tinput\t0\n')
            (root/'timing-summary.tsv').write_text(
                'setup_checks\t'+str(setup_count)+'\nhold_checks\t0\ncheck_setup\t1\n'
                'time_unit_seconds\t1e-9\ncapacitance_unit_farads\t1e-15\n'
                'connected_clock_fanout\t3\nclock\tcore\t1\n'
                'capacitance\t0\t1\t10\nslew\t0\t.1\t.2\nfanout\t0\t1\t10\n')
            result=inspect_timing(root,'',{})
            self.assertEqual(result['qualified_passive_count'],0)
            self.assertEqual(result['timed_endpoints']['endpoint_count'],1)
            self.assertEqual(result['timed_endpoints'],result['original_strict'])
            self.assertFalse((root/'typed-endpoints').exists())
            return result
    def test_positive(self):self.assertTrue(self.run_case('.1\t.01')['passed'])
    def test_unconstrained_real_endpoint(self):self.assertFalse(self.run_case('INF\tINF')['passed'])
    def test_setup_negative(self):self.assertFalse(self.run_case('-.001\t.01')['passed'])
    def test_hold_negative(self):self.assertFalse(self.run_case('.1\t-.001')['passed'])
    def test_native_count(self):self.assertFalse(self.run_case('.1\t.01',1)['passed'])

if __name__=='__main__':unittest.main()
