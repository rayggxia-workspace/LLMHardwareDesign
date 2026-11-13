from copy import deepcopy
from itertools import combinations
import random
import unittest

from loop_dp import search
from test_loop_dp import binding
from topology_diagnostics import diagnose,maximal_unions


class TestTopologyDiagnostics(unittest.TestCase):
    def test_single_metal_prevents_borrowing_both_incompatible_fast_instances(self):
        h={'sites':{'S':{'words':8}},'resources':{'a':1,'b':1},
           'resource_pools':{'compute':['a','b']},'nets':{n:{'cost':1} for n in ('x','y')}}
        tasks=[{'id':str(i),'bindings':[binding('a','a',10,['x']),binding('b','b',10,['y'])]} for i in range(2)]
        plan=search(tasks,h,width=32,wire_budget=1)
        before=deepcopy((tasks,h,plan));r=diagnose(tasks,h,plan,1)
        self.assertEqual(r['unconditioned_completion_lower_bound'],10)
        self.assertEqual(r['completion_lower_bound'],20)
        self.assertEqual(r['maximum_time_reduction_fraction_with_current_actions'],0)
        self.assertEqual(r['topology_count'],2);self.assertEqual(before,(tasks,h,plan))

    def test_complete_bundle_unions_cover_every_legal_product_small_random_hardware(self):
        rng=random.Random(22123)
        for trial in range(60):
            names=list('abcde');fixed={'a'} if trial%3 else set();budget=rng.randrange(1,7)
            h={'nets':{n:{'cost':rng.randrange(3),'fixed':n in fixed} for n in names},
               'incompatible_nets':[['b','c']] if trial%2 else []}
            tasks=[{'bindings':[{'nets':rng.sample(names,rng.randrange(3))} for _ in range(3)]} for _ in range(3)]
            maximal=maximal_unions(tasks,h,budget)
            self.assertIsNotNone(maximal)
            for size in range(6):
                for chosen in combinations(names,size):
                    union=set(chosen)|fixed
                    if sum(h['nets'][n]['cost'] for n in union-fixed)>budget:continue
                    if any(set(p)<=union for p in h['incompatible_nets']):continue
                    if not all(any(set(b['nets'])<=union for b in t['bindings']) for t in tasks):continue
                    # Unused nets need not be included, but every executable
                    # binding available on this product must remain available.
                    available=[set(b['nets']) for t in tasks for b in t['bindings'] if set(b['nets'])<=union]
                    self.assertTrue(any(all(b<=m for b in available) for m in maximal),(trial,union,maximal))

    def test_cutoff_is_explicit_and_never_uses_partial_topology_minimum(self):
        h={'sites':{'S':{'words':8}},'resources':{'a':1,'b':1},'nets':{n:{'cost':1} for n in ('x','y')}}
        tasks=[{'id':'t','bindings':[binding('a','a',10,['x']),binding('b','b',20,['y'])]}]
        plan=search(tasks,h,width=8,wire_budget=1);r=diagnose(tasks,h,plan,1,limit=1)
        self.assertFalse(r['enumeration_complete']);self.assertIsNone(r['topologies'])
        self.assertEqual(r['completion_lower_bound'],r['unconditioned_completion_lower_bound'])
        with self.assertRaises(ValueError):maximal_unions(tasks,h,1,limit=0)


if __name__=='__main__':unittest.main()
