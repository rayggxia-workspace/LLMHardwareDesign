"""Control-only gates for the private min/max experiment, not EDA results."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from audit import Invalid,file_sha
from build_min_probe import patch_source
from native_pair import run,verify
from output_path_control import scenario_sdc
import test_native_receipt


class PatchScope(unittest.TestCase):
    def test_finite_driver_load_scenario_preserves_other_constraints(self):
        self.assertIn('set_load 10 [get_ports q]',scenario_sdc('BUF_X1',10))
        for load in [float('nan'),float('inf'),-1,True]:
            with self.assertRaisesRegex(Invalid,'driver/load scenario'):
                scenario_sdc('BUF_X1',load)

    def test_exact_two_edits_and_explicit_modified_source_notice(self):
        before='// upstream license\nmin_max_(MinMax::max()),\nconst MinMax *min_max = MinMax::max();\n'
        after=patch_source(before)
        self.assertTrue(after.startswith('// QA127 MODIFIED SOURCE:'))
        self.assertIn('// upstream license',after)
        self.assertIn('min_max_(MinMax::min()),',after)
        self.assertIn('const MinMax *min_max = min_max_;',after)

    def test_missing_or_duplicate_patch_target_is_rejected(self):
        for text in ['', 'min_max_(MinMax::max()),'*2+'const MinMax *min_max = MinMax::max();']:
            with self.assertRaisesRegex(Invalid,'exact two edits'):
                patch_source(text)

    def test_driver_patch_does_not_change_clock_launched_output_arrival(self):
        text='''#include "Path.hh"
min_max_(MinMax::max()),
const MinMax *min_max = MinMax::max();
Arrival data_delay = src_path->arrival();
          Arrival delay = path->arrival();
          OutputDelays &delays = output_pin_delays[output_pin];
          Arrival delay = path->arrival();
          RiseFallMinMax &delays = clk_delays[clk_edge];
'''
        changed=patch_source(text,True,'max')
        self.assertIn('min_max_(MinMax::max()),',changed)
        self.assertIn('Arrival delay = path->arrival();\n          RiseFallMinMax &delays = clk_delays[clk_edge];',changed)
        self.assertEqual(changed.count('boundary_start->arrival()'),2)

    def test_driver_patch_rejects_unsupported_boundary_source(self):
        with self.assertRaisesRegex(Invalid,'driver-boundary patch target'):
            patch_source('min_max_(MinMax::max()),\nconst MinMax *min_max = MinMax::max();',True)


class SplitModelGates(unittest.TestCase):
    def setUp(self):
        self.fixture=test_native_receipt.NativeReceiptControls()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def declare(self):
        f=self.fixture
        model=f.request_path.parent/'min-lib'
        model.write_text('synthetic min Liberty')
        f.request['files']['macro_min_lib']={'path':str(model),'sha256':file_sha(model)}
        f.request['macro_delay_model']='split-min-max'
        f.request_path.write_text(json.dumps(f.request))

    def test_split_library_identity_is_preserved_and_recomputed(self):
        self.declare()
        f=self.fixture
        f.execute()
        with patch('native_pair.tcl_list',return_value='synthetic-library-list'):
            self.assertTrue(verify(f.output,f.request_path)['passed'])

    def test_resealed_wrong_loading_side_is_rejected(self):
        self.declare()
        f=self.fixture
        f.execute()
        path=f.output/'receipt.json'
        receipt=json.loads(path.read_text())
        abstract=next(r for r in receipt['commands'] if r['view']=='abstract')
        abstract['environment']['BV1QA_MIN_LIB']=abstract['environment']['BV1QA_MAX_LIB']
        path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(Invalid,'split model native loading binding'),patch('native_pair.tcl_list',return_value='synthetic-library-list'):
            verify(f.output,f.request_path)

    def test_missing_min_library_or_missing_declaration_is_rejected(self):
        self.declare()
        f=self.fixture
        del f.request['macro_delay_model']
        f.request_path.write_text(json.dumps(f.request))
        with self.assertRaisesRegex(Invalid,'min Liberty declaration'):
            run(f.request_path,f.output,f.executable)

    def test_split_diagnostic_cannot_masquerade_as_published_candidate(self):
        self.declare()
        f=self.fixture
        f.request['evidence_kind']='native-candidate-diagnostic'
        f.request_path.write_text(json.dumps(f.request))
        with self.assertRaisesRegex(Invalid,'control-only'):
            run(f.request_path,f.output,f.executable)


if __name__=='__main__':
    unittest.main()
