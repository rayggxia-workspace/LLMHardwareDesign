import unittest
from collections import Counter
from copy import deepcopy
from unittest.mock import patch

import numpy as np

from dot_cache import variants
from dot_cache_replay import DotCache,order_program
from loop_dp import optimize
from preparation_reuse import lower as prepare
from primitive_stages import lower
from streaming_ir import compile_graph
from test_dot_cache import example
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost


def plain():
    ir=example()
    for task in ir['tasks']:
        task['bindings']=[b for b in task['bindings'] if 'read_cache' not in b]
    ir.pop('read_cache_scope')
    return ir


def fork():
    src=plain();h=src['hardware'];group='normal';site=group+'.S';port=site+'.IO'
    h['sites'][site]={'words':64}
    h['resources'].update({group+'.N':1,group+'.LC.service':1,port:1})
    h['leaf_inventory'][group]={'macros':['N'],'site':site,'io_resource':port,
        'io_read_ticks':3,'io_write_ticks':3,'memory_group':1}
    for direction in ('read','write'):h['nets'][group+'.N.'+direction]={'cost':1,'fixed':False}
    program=deepcopy(src['primitive_program'])
    # Two independent branches inside one old kernel, then a true data join.
    program['instructions'].extend([
        {'id':'factor','kernel':'mm','op':'NFactor','inputs':['a'],'shape':[2,1],
         'bits':32,'exponent':0,'attributes':{'mode':1,'epsilon':1,'length':5}},
        {'id':'view','kernel':'mm','op':'View','inputs':['v'],'shape':[2,3],
         'bits':32,'exponent':0,'attributes':{}},
        {'id':'join','kernel':'mm','op':'Add','inputs':['view','factor'],'shape':[2,3],
         'bits':32,'exponent':0,'attributes':{'shift':0,'signs':[1,1]}}])
    program['outputs']={'out':'join'}
    with patch('streaming_ir.duration',return_value=1):
        return compile_graph(src['model'],h,[{'id':'mm','shape':[2,3],'exponent':0}],{},program)


class TestPrimitiveStages(unittest.TestCase):
    def audit(self,ir):
        with patch('verify_primitive_cost.duration',return_value=1):return verify_cost(ir)

    def test_work_traffic_conservation_and_independent_branches(self):
        coarse=prepare(fork());old_work=Counter(coarse['program'][0]['primitive_counts'])
        staged=lower(deepcopy(coarse));self.audit(staged)
        new_work=Counter()
        for row in staged['program']:new_work.update(row['primitive_counts'])
        self.assertEqual(new_work,old_work)
        tasks={t['id']:t for t in staged['tasks']}
        self.assertEqual(tasks['v#prepare-A']['after'],[])
        self.assertEqual(tasks['factor']['after'],[])
        self.assertEqual(tasks['v']['after'],['v#prepare-A'])
        self.assertEqual(tasks['join']['after'],['factor','v'])
        self.assertEqual(set(tasks['v']['bindings'][0]['macro_binding']),{'M'})
        old=optimize(coarse['tasks'],coarse['hardware'],width=8)
        new=optimize(staged['tasks'],staged['hardware'],width=8)
        verify(staged['tasks'],staged['hardware'],new)
        self.assertLess(new['makespan'],old['makespan'])
        self.assertEqual(new['external_words'],old['external_words'])
        ordered=order_program(staged['primitive_program'],new,staged['primitive_stages'])
        names=[n['id'] for n in ordered['instructions']]
        self.assertLess(names.index('v'),names.index('join'))
        self.assertLess(names.index('factor'),names.index('join'))

    def test_replay_consumes_selected_cache_and_prepared_records(self):
        ir=variants(lower(prepare(plain())),state_cost=True);self.audit(ir)
        plan=optimize(ir['tasks'],ir['hardware']);verify(ir['tasks'],ir['hardware'],plan)
        ordered=order_program(ir['primitive_program'],plan,ir['primitive_stages'])
        rng=np.random.default_rng(220)
        a=rng.integers(-(1<<31),1<<31,size=(2,5),dtype=np.int64)
        b=rng.integers(-32768,32768,size=(5,3),dtype=np.int64)
        cache=DotCache(ir,plan)
        np.testing.assert_array_equal(cache.dot(ordered['instructions'][0],a,b),a@b)
        self.assertEqual(cache.report()['preparation']['calls'],1)
        bad=deepcopy(plan);bad['tasks']=[r for r in bad['tasks'] if r['id']!='v#prepare-A']
        with self.assertRaisesRegex(ValueError,'omits operand preparation'):
            order_program(ir['primitive_program'],bad,ir['primitive_stages'])

    def test_checker_rejects_missing_edges_source_and_scratch_alias(self):
        ir=lower(prepare(fork()));self.audit(ir)
        for mutate in (
            lambda x:x['tasks'][-1].update(after=['v']),
            lambda x:x['primitive_stages']['v'].update(prepare='factor'),
            lambda x:x['program'][0].update(source_primitive='factor'),
            lambda x:x['program'][0]['temporary_external_region'].update(address_words=0),
            lambda x:x['program'][0]['temporary_external_region'].update(words=0),
            lambda x:x['program'][0]['body'].update(repeat=0),
        ):
            bad=deepcopy(ir);mutate(bad)
            with self.assertRaises(ValueError):self.audit(bad)

    def test_failure_is_atomic_and_no_free_scratch(self):
        ir=prepare(plain());ir['hardware']['external_capacity_words']=ir['required_external_bytes']//16
        before=deepcopy(ir)
        with self.assertRaisesRegex(ValueError,'capacity'):lower(ir)
        self.assertEqual(ir,before)
        with self.assertRaisesRegex(ValueError,'before cache'):lower(example())
        ir=lower(plain());self.audit(ir)
        with self.assertRaisesRegex(ValueError,'already'):lower(ir)

    def test_forward_primitive_reference_is_rejected(self):
        ir=prepare(fork());ir['primitive_program']['instructions'].reverse()
        with self.assertRaisesRegex(ValueError,'before use'):lower(ir)


if __name__=='__main__':unittest.main()
