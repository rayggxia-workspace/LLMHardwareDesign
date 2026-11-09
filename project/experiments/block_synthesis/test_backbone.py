from copy import deepcopy
import unittest

from loop_dp import search
from test_column_shards import fixture
from test_dot_cache import example
from test_loop_dp import binding
from verify_loop_dp import verify


class TestIncumbentBackbone(unittest.TestCase):
    def test_all_costs_and_cache_actions_replayed_and_independently_checked(self):
        ir=example(columns=9);tasks,h=ir['tasks'],ir['hardware']
        incumbent=search(tasks,h,width=8)
        result=search(tasks,h,width=8,backbone=incumbent)
        verify(tasks,h,result)
        self.assertEqual(result['backbone']['slot_budget'],8)
        self.assertEqual(result['backbone']['replayed_prefixes'],len(tasks))
        self.assertEqual(result['external_words'],incumbent['external_words'])
        for kwargs in ({'width':1},{'width':8,'decision_order':[t['id'] for t in tasks]}):
            with self.assertRaises(ValueError):search(tasks,h,backbone=incumbent,**kwargs)

    def test_seed_is_checked_and_compound_child_policies_are_not_guessed(self):
        ir=fixture(columns=9);p=search(ir['tasks'],ir['hardware'],width=8)
        result=search(ir['tasks'],ir['hardware'],width=8,backbone=p)
        verify(ir['tasks'],ir['hardware'],result)
        bad=deepcopy(p);bad['tasks'][-1]['end']-=1
        with self.assertRaises(ValueError):search(ir['tasks'],ir['hardware'],width=8,backbone=bad)

    def test_prefix_survives_within_fixed_width_even_when_bound_dislikes_it(self):
        h={'resources':{'a':1,'b':1},'sites':{'S':{'words':64}},'nets':{}}
        tasks=[{'id':str(i),'bindings':[binding('a','a',i+2),binding('b','b',9-i)]} for i in range(5)]
        incumbent=search(tasks,h,width=32,ready_limit=5,rank_policy='net_resource_tail')
        result=search(tasks,h,width=2,ready_limit=1,backbone=incumbent)
        verify(tasks,h,result)
        self.assertGreater(result['backbone']['forced_prefix_slots'],0)
        self.assertEqual(result['backbone']['slot_budget'],2)
        self.assertLessEqual(result['makespan'],incumbent['makespan'])
