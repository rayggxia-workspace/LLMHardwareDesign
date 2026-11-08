from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from dot_cache_replay import DotCache
from full_integer import round_shift
from phase_accounting import account as phase_account
from traffic_accounting import account as traffic_account
from utilization import report as utilization
from loop_dp import search
from test_column_shards import fixture as column_fixture,initial
from test_tile_recipe import fixture as service_fixture
from tile_bindings import variants_for as register_tiles
from tile_accounting import charge,traffic
from transition import evaluate_transition,retention_actions
from verify_loop_dp import verify as verify_schedule
from verify_primitive_cost import verify as verify_cost
from wide_program import execute


def fixture(**kwargs):
    ir=column_fixture(words=1024,**kwargs)
    node=ir['primitive_program']['instructions'][0]
    k=node['attributes']['length'];n=node['shape'][-1]
    ir['primitive_program']['initial_formats']['b'].update(
        shape=[k,n],source_file='synthetic-static-B-only-for-unit-tests.npy')
    return ir,service_fixture()[1]


def variants_for(ir,q):
    declarations={'kind':'native-tile-instance-services-v1',
        'qualification_sha256':hashlib.sha256(json.dumps(q,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'P':[g for g,m in ir['hardware']['leaf_inventory'].items() if 'M' in m['macros']],
        'E':[g for g,m in ir['hardware']['leaf_inventory'].items() if 'E' in m['macros']],
        'evidence':'synthetic unit-test service assignments, not product qualification'}
    return register_tiles(ir,q,service_bindings=declarations)


def tile_binding(ir,shape=(2,8)):
    task=next(t for t in ir['tasks'] if t['id']=='v')
    return next(b for b in task['bindings'] if b.get('dot_tile',{}).get('tile')==list(shape))


class TestTileBindings(unittest.TestCase):
    def audit(self,ir):
        with patch('verify_primitive_cost.duration',return_value=1):return verify_cost(ir)

    def test_shared_pool_and_independent_native_audit(self):
        ir,q=fixture(columns=9)
        old={t['id']:[deepcopy(b) for b in t['bindings']] for t in ir['tasks']}
        variants_for(ir,q);self.audit(ir)
        self.assertGreater(ir['tile_scope']['added_bindings'],0)
        for task in ir['tasks']:
            self.assertEqual(task['bindings'][:len(old[task['id']])],old[task['id']])
        for width in (1,8):
            plan=search(ir['tasks'],ir['hardware'],width=width)
            self.assertEqual(plan['status'],'planned')
            verify_schedule(ir['tasks'],ir['hardware'],plan)
        with self.assertRaises(ValueError):variants_for(ir,q)

    def test_E_leaf_letter_does_not_qualify_its_surrounding_service(self):
        ir,q=fixture()
        with self.assertRaisesRegex(ValueError,'instance-to-qualified-service'):register_tiles(ir,q)
        variants_for(ir,q)
        forged=deepcopy(ir);forged['hardware']['tile_service_bindings']['E']=[]
        with self.assertRaisesRegex(ValueError,'instance not qualified'):self.audit(forged)

    def test_tile_time_and_traffic_attribution_include_conversion(self):
        ir,q=fixture(columns=11);variants_for(ir,q)
        for task in ir['tasks']:
            for b in task['bindings']:
                if 'dot_tile' not in b:continue
                costs=charge(b,ir['hardware']);reads,writes=traffic(b)
                self.assertEqual(sum(costs.values()),b['ticks'])
                self.assertEqual(sum(reads.values())+sum(writes.values()),b['tile_work']['external_words'])
                if b['dot_tile']['tile'][1]>1:
                    self.assertGreater(reads['tile_scatter_basis_loads'],0)
                    self.assertGreater(costs['tile_E_service'],0)

    def test_no_unqualified_tail_or_dynamic_B(self):
        ir,q=fixture(columns=11)
        q['shapes'].remove([2,3]);variants_for(ir,q)
        self.assertFalse(any(b.get('dot_tile',{}).get('tile')==[2,8]
            for t in ir['tasks'] for b in t['bindings']))
        self.audit(ir)
        for changed in ('dynamic','batched'):
            ir,q=fixture()
            meta=ir['primitive_program']['initial_formats']['b']
            if changed=='dynamic':del meta['source_file']
            else:meta['shape']=[2]+meta['shape']
            variants_for(ir,q)
            self.assertEqual(ir['tile_scope']['added_bindings'],0)
            self.assertNotIn('tile_constants',ir)

    def test_native_cost_layout_constants_and_resources_cannot_be_forged(self):
        base,q=fixture();variants_for(base,q)
        mutations=[
            lambda ir,b:b['dot_tile'].update(prepared_A_base=0),
            lambda ir,b:b['dot_tile'].update(invalidate_read_cache=[]),
            lambda ir,b:b['dot_tile']['layout'].update(A=[0,2]),
            lambda ir,b:b['tile_work'].update(dot_A_loads=0),
            lambda ir,b:b.update(ticks=b['ticks']-1),
            lambda ir,b:b.update(external_read_words=b['external_read_words']-1),
            lambda ir,b:b['resources'].pop(),
            lambda ir,b:b['nets'].pop(),
            lambda ir,b:b['scratch_by_site'].update({b['site']:8}),
            lambda ir,b:ir['tile_constants']['records'][1].__setitem__(0,0),
            lambda ir,b:ir['tile_constants'].update(address_words=0),
            lambda ir,b:ir['hardware']['sites'][b['site']].update(words=511),
            lambda ir,b:ir['primitive_program']['initial_formats']['b'].pop('source_file'),
        ]
        for i,mutate in enumerate(mutations):
            with self.subTest(i=i):
                ir=deepcopy(base);mutate(ir,tile_binding(ir))
                with self.assertRaises(ValueError):self.audit(ir)

    def test_each_frontier_accounts_for_wait_and_cache_invalidation_without_mutation(self):
        ir,q=fixture();variants_for(ir,q);b=tile_binding(ir)
        state=initial(ir);site=b['site']
        state.cache[site]=('old-A',5,30)
        old=deepcopy(state);self.assertEqual(retention_actions(state,b),('invalidate',))
        ev=evaluate_transition(state,b,ir['hardware'],17,retention='invalidate')
        self.assertTrue(ev['legal']);self.assertEqual(state.__dict__,old.__dict__)
        self.assertNotIn(site,ev['cache']);self.assertEqual(ev['start'],17)
        self.assertEqual(ev['details']['discarded_read_cache'],
            [{'site':site,'tag':'old-A','prefix':5,'words':30}])
        state.resources[b['resources'][0]]=(1000,)
        delayed=evaluate_transition(state,b,ir['hardware'],17,retention='invalidate')
        self.assertEqual(delayed['end']-ev['end'],983)
        self.assertEqual(delayed['traffic'],ev['traffic'])
        self.assertFalse(evaluate_transition(state,b,ir['hardware'],0)['legal'])

    def test_cache_tile_cache_sequence_requires_cold_refill_and_honest_schedule(self):
        ir,q=fixture();variants_for(ir,q);h=ir['hardware']
        old=next(b for t in ir['tasks'] if t['id']=='v' for b in t['bindings']
                 if b.get('read_cache',{}).get('stripe')==5)
        tile=next(b for t in ir['tasks'] if t['id']=='v' for b in t['bindings']
                  if b.get('dot_tile',{}).get('tile')==[2,8] and b['site']==old['site'])
        tasks=[{'id':name,'after':[] if i==0 else [str(i-1)],'bindings':[b]}
               for i,(name,b) in enumerate((('0',old),('1',tile),('2',old)))]
        state=initial(ir);rows=[];traffic=0
        for task in tasks:
            b=task['bindings'][0]
            ev=evaluate_transition(state,b,h,state.makespan,
                retention='invalidate' if b.get('dot_tile') else 'preserve')
            self.assertTrue(ev['legal'])
            row={'id':task['id'],'binding':b['id'],'site':b['site'],
                 'start':ev['start'],'end':ev['end'],'evaluation':ev['details']}
            if b.get('read_cache'):row['cache_hit']=ev['cache_hit']
            rows.append(row);traffic+=ev['traffic']
            state=SimpleNamespace(**{key:ev[key] for key in ('resources','cache','nets','makespan')})
        self.assertFalse(rows[2]['cache_hit'])
        self.assertEqual(rows[2]['evaluation']['loaded_prefix'],5)
        plan={'status':'planned','tasks':rows,'makespan':state.makespan,'external_words':traffic,
              'nets':sorted(state.nets),'wire_cost':sum(h['nets'][n]['cost'] for n in state.nets)}
        verify_schedule(tasks,h,plan)
        forged=deepcopy(plan);forged['tasks'][1]['evaluation']['discarded_read_cache']=[]
        with self.assertRaises(ValueError):verify_schedule(tasks,h,forged)
        forged=deepcopy(plan);forged['tasks'][2]['cache_hit']=True
        with self.assertRaises(ValueError):verify_schedule(tasks,h,forged)

    def test_literal_finite_S_tile_values_tails_rounding_and_real_scalar_conversion(self):
        rng=np.random.default_rng(22071)
        for rt,ct,shift in ((1,1,0),(2,1,16),(1,8,8),(2,8,24),(2,4,16),(2,3,8)):
            with self.subTest(tile=(rt,ct),shift=shift):
                ir,q=fixture(columns=11,k=7)
                node=ir['primitive_program']['instructions'][0];node['attributes']['shift']=shift
                variants_for(ir,q);task=next(t for t in ir['tasks'] if t['id']=='v')
                task['bindings']=[tile_binding(ir,(rt,ct))]
                plan=search(ir['tasks'],ir['hardware'],width=1)
                verify_schedule(ir['tasks'],ir['hardware'],plan)
                a=rng.integers(-(1<<31),1<<31,size=(2,7),dtype=np.int64)
                b=rng.integers(-32768,32768,size=(7,11),dtype=np.int64)
                a[0,:4]=[-2147483648,-32769,-32768,2147483647]
                cache=DotCache(ir,plan)
                result=execute(ir['primitive_program'],{'a':a,'b':b},[[1,2]],None,dot_executor=cache)
                expected=np.clip(round_shift(a@b,shift),-(1<<31),(1<<31)-1)
                np.testing.assert_array_equal(result['out'].raw,expected)
                report=cache.report();self.assertEqual(report['tile_calls'],1)
                with patch('verify_primitive_cost.duration',return_value=1):
                    traffic_result=traffic_account(ir,plan)
                    occupancy=utilization(ir,plan)
                    phase_result=phase_account(ir,plan)
                self.assertEqual(traffic_result['total_logical_words'],plan['external_words'])
                self.assertEqual(sum(phase_result['serial_components'].values()),occupancy['serial_work'])
                event=report['tile_events'][0]
                self.assertLessEqual(event['peak_P_extent'],576)
                self.assertLessEqual(event['peak_external_tmp'],32)
                if ct>1:self.assertGreater(event['counts']['scatter_executes'],0)

    def test_corrupted_basis_cannot_silently_return_reference_matmul(self):
        ir,q=fixture(columns=8,k=3);variants_for(ir,q)
        task=next(t for t in ir['tasks'] if t['id']=='v');task['bindings']=[tile_binding(ir)]
        plan=search(ir['tasks'],ir['hardware'],width=1)
        # Simulate bad deployed constant data after independent plan validation.
        cache=DotCache(ir,plan);cache.tiles.constants=deepcopy(ir['tile_constants'])
        cache.tiles.constants['records'][1][0]=0
        a=np.array([[1,2,3],[4,5,6]],dtype=np.int64);b=np.ones((3,8),dtype=np.int64)
        with self.assertRaisesRegex(ValueError,'tile/scatter final differs'):
            execute(ir['primitive_program'],{'a':a,'b':b},[[1,2]],None,dot_executor=cache)


if __name__=='__main__':unittest.main()
