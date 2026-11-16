from copy import deepcopy
import random
import unittest
from unittest.mock import patch

import numpy as np

from column_shards import expand_selected
from dot_cache_replay import DotCache
from loop_dp import search,optimize
from phase_survey import expanded
from phase_trace import reference
from phased_compounds import variants_for,eligible
from test_column_shards import fixture,initial
from transition import evaluate_transition
from verify_loop_dp import verify
from verify_phased_compounds import _program
from verify_primitive_cost import verify as verify_cost
from utilization import report
from phase_accounting import account
from traffic_accounting import account as traffic
from service_bounds import optimistic_ticks


def example(**kwargs):return variants_for(fixture(shared=True,**kwargs))


def candidate(ir):
    return next(b for t in ir['tasks'] for b in t['bindings'] if 'phase_execution' in b and
        all(c['binding']['read_cache']['stripe']==5 for c in b['parallel_shards']['children']))


class TestPhasedCompounds(unittest.TestCase):
    def test_common_pool_preserves_old_choices_and_numeric_values(self):
        ir=example();task=next(t for t in ir['tasks'] if t['id']=='v')
        self.assertTrue(any('phase_execution' not in b for b in task['bindings']))
        with patch('verify_primitive_cost.duration',return_value=1):verify_cost(ir)
        old=deepcopy(ir);next(t for t in old['tasks'] if t['id']=='v')['bindings']=[b for b in task['bindings'] if 'phase_execution' not in b]
        before=optimize(old['tasks'],old['hardware'],width=8)
        plan=optimize(ir['tasks'],ir['hardware'],width=8,incumbents=[before])
        self.assertLessEqual(plan['makespan'],before['makespan']);verify(ir['tasks'],ir['hardware'],plan)
        rng=np.random.default_rng(219);a=rng.integers(-(1<<31),1<<31,size=(2,5),dtype=np.int64)
        b=rng.integers(-32768,32768,size=(5,9),dtype=np.int64)
        cache=DotCache(ir,plan)
        np.testing.assert_array_equal(cache.dot(ir['primitive_program']['instructions'][0],a,b),a@b)
        cache.report()

    def test_every_frontier_recomputes_prefix_and_owns_full_resource_union(self):
        ir=example();b=candidate(ir);h=ir['hardware'];s=initial(ir)
        cold=evaluate_transition(s,b,h,0,retention=('preserve','preserve'))
        c=b['parallel_shards']['children'][0]['binding']['read_cache']
        s.cache[c['site']]=(c['tag'],2,2*c['rows']*c['components'][0])
        hot=evaluate_transition(s,b,h,0,retention=('preserve','preserve'))
        self.assertEqual(cold['traffic']-hot['traffic'],2*c['rows']*c['components'][0])
        self.assertEqual(hot['details']['services'][0]['evaluation']['reused_prefix'],2)
        resource=next(r for r in b['resources'] if r.endswith('.M'))
        s.resources[resource]=(100000,)
        delayed=evaluate_transition(s,b,h,0,retention=('preserve','preserve'))
        self.assertEqual(delayed['start'],100000)
        self.assertEqual(delayed['end']-delayed['start'],hot['duration'])
        self.assertTrue(all(delayed['resources'][r]==(delayed['end'],) for r in b['resources']))

    def test_cost_matches_independently_expanded_fcfs_events(self):
        for seed in range(25):
            rng=random.Random(seed);ir=example(columns=rng.randint(3,11),k=rng.randint(2,9))
            b=next(b for t in ir['tasks'] for b in t['bindings'] if 'phase_execution' in b)
            ev=evaluate_transition(initial(ir),b,ir['hardware'],0,retention=('preserve',)*len(b['parallel_shards']['children']))
            workers=[expanded(_program(c['binding'],s,ir['hardware']))
                for c,s in zip(b['parallel_shards']['children'],ev['details']['services'])]
            self.assertEqual(ev['duration'],reference(workers,ir['hardware']['virtual_memory']['channels'])['makespan'])

    def test_unknown_protocol_phase_times_and_waits_are_rejected(self):
        ir=example();task=next(t for t in ir['tasks'] if t['id']=='v');task['bindings']=[candidate(ir)]
        plan=optimize(ir['tasks'],ir['hardware']);verify(ir['tasks'],ir['hardware'],plan)
        for field in ('wait','event','end','protocol','grammar','pretend-legacy'):
            source=deepcopy(ir);bad=deepcopy(plan);row=bad['tasks'][-1]
            if field=='wait':row['evaluation']['services'][0]['evaluation']['channel_wait_ticks']+=1
            elif field=='event':row['evaluation']['phase_timing']['phase_counts']['M']+=1
            elif field=='end':row['end']-=1
            elif field=='protocol':source['tasks'][-1]['bindings'][0]['phase_execution']['reservation']='none'
            elif field=='grammar':source['hardware']['phase_native_templates']['partial']['sequence'][0]['ticks']+=1
            else:row['evaluation']['cost_model']='dot-column-shards-v1';row['evaluation'].pop('phase_timing')
            with self.assertRaises((ValueError,KeyError)):verify(source['tasks'],source['hardware'],bad)
        changed=deepcopy(ir);changed['hardware']['phase_native_templates']['partial']['sequence'][0]['ticks']+=1
        with patch('verify_primitive_cost.duration',return_value=1),self.assertRaisesRegex(ValueError,'templates differ'):
            verify_cost(changed)

    def test_shared_private_resource_or_missing_queue_capacity_is_not_admitted(self):
        ir=example();b=candidate(ir)
        private=next(r for r in b['parallel_shards']['children'][0]['binding']['resources'] if r.endswith('.M'))
        bad=deepcopy(b);bad['parallel_shards']['children'][1]['binding']['resources'].append(private)
        self.assertFalse(eligible(bad,ir['hardware']))
        h=deepcopy(ir['hardware']);h['virtual_memory']['credits']=1
        self.assertFalse(eligible(b,h))
        separate=fixture();variants_for(separate)
        self.assertEqual(separate['phased_compound_scope']['added_bindings'],0)

    def test_heterogeneous_recipes_keep_only_original_serial_choices(self):
        ir=example();b=candidate(ir);bad=deepcopy(b)
        bad['parallel_shards']['children'][0]['binding']['read_cache']['stripe']-=1
        self.assertFalse(eligible(bad,ir['hardware']))
        self.assertEqual(optimistic_ticks(b),max(c['binding']['warm_ticks'] for c in b['parallel_shards']['children']))
        from search_diagnostics import bounds
        plan=search(ir['tasks'],ir['hardware'],width=8)
        self.assertLessEqual(bounds(ir['tasks'],ir['hardware'],plan)['completion_lower_bound'],plan['makespan'])

    def test_accounting_does_not_charge_arbitration_as_extra_loads(self):
        ir=example();next(t for t in ir['tasks'] if t['id']=='v')['bindings']=[candidate(ir)]
        plan=optimize(ir['tasks'],ir['hardware'])
        with patch('verify_primitive_cost.duration',return_value=1):
            profile=report(ir,plan);parts=account(ir,plan);moved=traffic(ir,plan)
        self.assertGreater(profile['arbitration_wait_work'],0)
        self.assertEqual(moved['total_logical_words'],plan['external_words'])
        task=next(t for t in ir['tasks'] if t['id']=='v');b=task['bindings'][0]
        row=next(r for r in plan['tasks'] if r['id']=='v')
        self.assertTrue(all(profile['resources'][r]['reserved_ticks']>=row['end']-row['start'] for r in b['resources']))
        self.assertTrue(all(c['whole_service_reserved_ticks']>=c['descriptor_demand_ticks'] for c in parts['channels'].values()))


if __name__=='__main__':unittest.main()
