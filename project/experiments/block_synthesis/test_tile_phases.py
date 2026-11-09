from collections import Counter
from copy import deepcopy
import random
import unittest
from unittest.mock import patch

import numpy as np

from dot_cache_replay import DotCache
from loop_dp import search
from phase_accounting import account
from phase_program import aggregate,simulate
from phase_trace import reference
from test_column_shards import initial
from test_phase_program import expand
from test_tile_partitions import example
from tile_phases import eligible,program,timing_key,worker
from transition import evaluate_transition,retention_actions
from utilization import report
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost
from verify_tile_phases import program as independent_program
from wide_program import execute


def candidate(ir):
    return next(b for t in ir['tasks'] for b in t['bindings'] if 'tile_partition' in b and
        'phase_execution' in b and all(c['binding']['dot_tile']['tile'][1]>1 for c in b['parallel_shards']['children']))


class TestTilePhases(unittest.TestCase):
    def test_multiple_real_Dot_stages_do_not_overwrite_generation_counters(self):
        from test_tile_bindings import fixture,variants_for as register_tiles
        from streaming_ir import compile_graph
        from preparation_reuse import lower as prepare
        from primitive_stages import lower
        from tile_partitions import variants_for
        original,q=fixture(columns=17,shared=True)
        model={'values':{'a':{'shape':[2,5]},'b':{'shape':[5,17]},
                         'out':{'shape':[2,17]},'out2':{'shape':[2,17]}},
            'tasks':[{'id':name,'op':'MatMul','inputs':['a','b'],'outputs':[out]}
                     for name,out in (('mm','out'),('mm2','out2'))]}
        prototype=deepcopy(original['primitive_program']['instructions'][0])
        program={'initial_formats':deepcopy(original['primitive_program']['initial_formats']),
                 'outputs':{'out':'v','out2':'w'},'instructions':[prototype,{**prototype,'id':'w','kernel':'mm2'}]}
        with patch('streaming_ir.duration',return_value=1):
            ir=compile_graph(model,deepcopy(original['hardware']),[
                {'id':name,'shape':[2,17],'exponent':0} for name in ('mm','mm2')],{},program)
        ir=lower(prepare(ir));register_tiles(ir,q);variants_for(ir,phased=True)
        self.assertEqual(ir['tile_partition_scope']['eligible_tasks'],2)
        self.assertGreater(ir['tile_partition_scope']['phased_added_bindings'],0)
        with patch('verify_primitive_cost.duration',return_value=1):verify_cost(ir)

    def test_common_pool_preserves_older_partitions_and_independent_costs(self):
        old=example(two_e=True);new=example(two_e=True,phased=True)
        self.assertGreater(new['tile_partition_scope']['phased_added_bindings'],0)
        for a,b in zip(old['tasks'],new['tasks']):self.assertEqual(b['bindings'][:len(a['bindings'])],a['bindings'])
        with patch('verify_primitive_cost.duration',return_value=1):verify_cost(new)

    def test_solo_best_grid_does_not_erase_compatible_cooperative_tail(self):
        ir=example(19,two_e=True,k=7,phased=True,shared=True)
        choices=[b for t in ir['tasks'] for b in t['bindings'] if 'tile_partition' in b and 'phase_execution' in b]
        self.assertTrue(any(all(c['binding']['dot_tile']['tile']==[2,8] for c in b['parallel_shards']['children']) for b in choices))
        with patch('verify_primitive_cost.duration',return_value=1):verify_cost(ir)

    def test_every_phase_conserves_native_work_and_order_against_independent_expansion(self):
        rng=random.Random(220110)
        for _ in range(25):
            ir=example(rng.randint(3,24),two_e=True,k=rng.randint(1,9),phased=True,shared=True);h=ir['hardware']
            bindings=[b for t in ir['tasks'] for b in t['bindings'] if 'phase_execution' in b and 'tile_partition' in b]
            b=rng.choice(bindings);programs=[]
            for child in b['parallel_shards']['children']:
                leaf=child['binding'];p,t,counts=worker(timing_key(leaf,h));independent=independent_program(leaf,h)
                self.assertEqual(expand(p),expand(independent))
                self.assertEqual(t,leaf['ticks']);self.assertEqual(counts['external-load-until-S-commit'],leaf['external_read_words'])
                self.assertEqual(counts['external-store-until-ACK'],leaf['external_write_words'])
                w=leaf['tile_work']
                for label,expected in (('tile-scale',w['dot_scales']+w.get('scatter_scales',0)),
                    ('tile-execute',w['dot_executes']+w.get('scatter_executes',0)),
                    ('tile-feeder',w['dot_feeds']+w.get('scatter_feeds',0)),
                    ('tile-final-store',w['final_reads']),('tile-E-service',w.get('e_sign_services',0))):
                    self.assertEqual(counts[label],expected)
                programs.append(p)
            expected=reference([expand(p) for p in programs],h['virtual_memory']['channels'])
            ev=evaluate_transition(initial(ir),b,h,0,retention=retention_actions(initial(ir),b)[0])
            self.assertEqual(ev['duration'],expected['makespan'])
            self.assertEqual(ev['duration'],simulate(programs,h['virtual_memory']['channels'],fast_forward=False)['makespan'])

    def test_frontier_wait_union_lease_and_finite_S_numeric(self):
        ir=example(two_e=True,phased=True,shared=True);b=candidate(ir);h=ir['hardware'];state=initial(ir)
        before=deepcopy(vars(state));policies=retention_actions(state,b)[0]
        ev=evaluate_transition(state,b,h,0,retention=policies);self.assertEqual(vars(state),before)
        self.assertTrue(all(ev['resources'][r]==(ev['end'],) for r in b['resources']))
        busy=deepcopy(state);busy.resources[b['resources'][0]]=(100000,)
        delayed=evaluate_transition(busy,b,h,0,retention=policies)
        self.assertEqual(delayed['start'],100000);self.assertEqual(ev['duration'],delayed['duration'])
        next(t for t in ir['tasks'] if t['id']=='v')['bindings']=[b]
        for width in (1,8):
            p=search(ir['tasks'],h,width=width);verify(ir['tasks'],h,p)
            with patch('verify_primitive_cost.duration',return_value=1):
                parts=account(ir,p);usage=report(ir,p)
            self.assertEqual(sum(parts['serial_components'].values()),usage['serial_work'])
            self.assertGreater(usage['arbitration_wait_work'],0)
            a=np.arange(10,dtype=np.int64).reshape(2,5)*65537-32769
            weights=np.arange(85,dtype=np.int64).reshape(5,17)-42
            cache=DotCache(ir,p);result=execute(ir['primitive_program'],{'a':a,'b':weights},[[1,2]],None,dot_executor=cache)
            np.testing.assert_array_equal(result['out'].raw,np.clip(a@weights,-(1<<31),(1<<31)-1));cache.report()

    def test_full_K_long_grid_keeps_all_events_and_boundary_tails(self):
        ir=example(64,two_e=True,k=2048,phased=True,shared=True);b=candidate(ir);h=ir['hardware']
        programs=[worker(timing_key(c['binding'],h))[0] for c in b['parallel_shards']['children']]
        result=simulate(programs,h['virtual_memory']['channels'],event_limit=100000)
        counts=Counter()
        for p in programs:counts.update(aggregate(p)[1])
        self.assertEqual(result['phase_counts'],dict(counts))
        self.assertGreater(result['skipped_events'],10000)
        self.assertLess(result['executed_events'],100000)

    def test_forged_wait_events_protocol_shared_private_and_credit_rejected(self):
        source=example(two_e=True,phased=True);b=candidate(source)
        next(t for t in source['tasks'] if t['id']=='v')['bindings']=[b]
        p=search(source['tasks'],source['hardware'],width=1);verify(source['tasks'],source['hardware'],p)
        for field in ('wait','event','end','protocol','credit'):
            ir=deepcopy(source);bad=deepcopy(p);row=bad['tasks'][-1]
            if field=='wait':row['evaluation']['services'][0]['evaluation']['channel_wait_ticks']+=1
            elif field=='event':row['evaluation']['phase_timing']['phase_counts']['tile-execute']+=1
            elif field=='end':row['end']-=1
            elif field=='protocol':ir['tasks'][-1]['bindings'][0]['phase_execution']['reservation']='none'
            else:ir['hardware']['virtual_memory']['credits']=1
            with self.assertRaises(ValueError):verify(ir['tasks'],ir['hardware'],bad)
        bad=deepcopy(b);bad['parallel_shards']['children'][1]['binding']['resources'].append(
            next(r for r in b['parallel_shards']['children'][0]['binding']['resources'] if r.endswith('.M')))
        self.assertFalse(eligible(bad,source['hardware']))
        ir=deepcopy(source);ir['tasks'][-1]['bindings']=[bad]
        with patch('verify_primitive_cost.duration',return_value=1):
            with self.assertRaises(ValueError):verify_cost(ir)


if __name__=='__main__':unittest.main()
