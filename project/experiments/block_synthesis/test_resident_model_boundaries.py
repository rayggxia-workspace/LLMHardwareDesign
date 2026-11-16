from copy import deepcopy
import unittest
from unittest.mock import patch

from native_pointwise import bind_external,execute,lower
from resident_model_boundaries import boundary_program
from resident_replay import replay
from resident_survey import run
from test_resident_bindings import fixture


class TestResidentBoundaryProgram(unittest.TestCase):
    def fixture(self):
        ir,timing=fixture();p=ir['primitive_program'];names=[n['id'] for n in p['instructions']]
        graph=bind_external(lower(p,names,0),ir)
        # The synthetic fixture's task bindings are deliberately placeholders;
        # the native program/survey/replay below are real, unmocked operations.
        with patch('resident_survey.verify'):
            survey=run(ir,[{'graphs':[graph]}],cases=1,width=4,service_timing=timing)
        return ir,timing,graph,survey

    def test_exported_full_program_survives_survey_to_actual_value_replay(self):
        ir,q,g,survey=self.fixture();row=survey['rows'][0];inputs={('x',0):-2147483648,('y',0):2147483647}
        gold=execute(g,inputs)
        for strategy in row['plans']:
            p=boundary_program(row,strategy,survey['actors'],ir['native_constants']['0']['address_words'],q)
            self.assertIs(p,row['programs'][strategy]);self.assertEqual(p['status'],'planned')
            actual=replay(g,p,inputs)['observed_native_outputs']
            self.assertEqual(actual,{n['output']:gold[n['output']] for n in g['operations']})

    def test_lossy_or_mismatched_program_is_rejected_without_inventing_status(self):
        ir,q,g,survey=self.fixture();row=survey['rows'][0];name=next(iter(row['plans']))
        bad=deepcopy(row);del bad['programs']
        with self.assertRaisesRegex(ValueError,'complete original'):
            boundary_program(bad,name,survey['actors'],ir['native_constants']['0']['address_words'],q)
        bad=deepcopy(row);bad['plans'][name]['total_ticks']-=1
        with self.assertRaisesRegex(ValueError,'complete original'):
            boundary_program(bad,name,survey['actors'],ir['native_constants']['0']['address_words'],q)


if __name__=='__main__':unittest.main()
