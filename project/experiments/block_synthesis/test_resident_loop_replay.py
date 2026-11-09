from copy import deepcopy
import unittest
import numpy as np

from full_integer import Q
from resident_bindings import uniform_contract,variants_for
from resident_loop_replay import Execution,element
from test_resident_bindings import fixture
from wide_program import execute


class TestResidentLoopReplay(unittest.TestCase):
    def test_all_elements_replace_original_arithmetic_and_match_integer_stream(self):
        ir,q=fixture();variants_for(ir,q,width=4)
        r=min(ir['resident_recipes'].values(),key=lambda r:r['plan']['total_ticks'])
        program=deepcopy(ir['primitive_program'])
        program['outputs']={n['id']:n['id'] for n in program['instructions']}
        initial={'x':Q(np.asarray([-2147483648,2147483647,-32769],dtype=np.int64),0),
                 'y':Q(np.asarray([32767,-32768,2147483647],dtype=np.int64),0),
                 'one':Q(np.asarray(1,dtype=np.int64),0)}
        gold=execute(program,initial,[],None);backend=Execution(program,[r])
        actual=execute(program,initial,[],None,region_executor=backend)
        for name in gold:np.testing.assert_array_equal(actual[name].raw,gold[name].raw)
        self.assertEqual(backend.report()['loops'][0]['elements'],3)
        graph,plan=element(r,2)
        for key,o in graph['objects'].items():
            if o['kind']=='external' and o['tensor']=='x':self.assertEqual(o['index'],2)
        self.assertEqual(len(plan['events']),len(r['plan']['events']))
        bad=deepcopy(r);next(e for e in bad['plan']['events'] if e['op']=='M_TERM')['coefficient']+=1
        with self.assertRaisesRegex(ValueError,'encoding'):execute(program,initial,[],None,region_executor=Execution(program,[bad]))

    def test_indexed_literals_and_incomplete_execution_are_rejected(self):
        ir,q=fixture();names=[n['id'] for n in ir['primitive_program']['instructions']]
        ir['primitive_program']['initial_formats']['one'].update(shape=[3],literal=[1,2,3])
        with self.assertRaisesRegex(ValueError,'indexed literal'):uniform_contract(ir,names)
        ir,q=fixture();variants_for(ir,q,width=4);r=next(iter(ir['resident_recipes'].values()))
        with self.assertRaisesRegex(ValueError,'not fully'):Execution(ir['primitive_program'],[r]).report()


if __name__=='__main__':unittest.main()
