from copy import deepcopy
import random
import unittest

from loop_dp import search
from selected_order_profile import profile
from test_loop_dp import binding


class TestSelectedOrderProfile(unittest.TestCase):
    def test_dependency_and_resource_handoffs_do_not_form_zero_time_cycles(self):
        h={'resources':{'a':1,'b':1},'sites':{'S':{'words':8}},'nets':{}}
        tasks=[{'id':'x','bindings':[binding('x','a',7)]},
               {'id':'y','after':['x'],'bindings':[binding('y','b',3)]},
               {'id':'z','after':['y'],'bindings':[binding('z','a',5)]}]
        p=search(tasks,h);before=deepcopy((tasks,h,p))
        result=profile(tasks,h,p,operators={'x':'Dot','y':'Add','z':'Dot'})
        self.assertEqual(result['selected_order_relaxed_lower_bound'],15)
        self.assertEqual(result['critical_chain_ticks_by_operator'],{'Dot':12,'Add':3})
        self.assertEqual(result['unexplained_or_rigid_wait_ticks'],0)
        self.assertEqual((tasks,h,p),before)

    def test_whole_service_chains_match_independent_resource_order_recurrence(self):
        for seed in range(80):
            rng=random.Random(seed);h={'resources':{'a':1,'b':1},'sites':{'S':{'words':8}},'nets':{}}
            tasks=[{'id':str(i),'after':[str(j) for j in range(i) if rng.random()<.25],
                    'bindings':[binding('b',rng.choice(['a','b']),rng.randint(1,10))]} for i in range(7)]
            p=search(tasks,h,width=1)
            # Independent task-level recurrence; no event vertices or helper.
            parents={t['id']:set(t['after']) for t in tasks};duration={t['id']:t['bindings'][0]['ticks'] for t in tasks}
            for resource in h['resources']:
                order=sorted((r['start'],r['id']) for r in p['tasks']
                    if resource in tasks[int(r['id'])]['bindings'][0]['resources'])
                for (_,a),(_,b) in zip(order,order[1:]):parents[b].add(a)
            finish={}
            def end(name):
                if name not in finish:finish[name]=duration[name]+max((end(n) for n in parents[name]),default=0)
                return finish[name]
            expected=max(end(t['id']) for t in tasks)
            r=profile(tasks,h,p)
            self.assertEqual(r['selected_order_relaxed_lower_bound'],expected)
            self.assertLessEqual(expected,p['makespan'])
            self.assertEqual(sum(x['ticks'] for x in r['critical_chain']),expected)

    def test_multi_capacity_is_colored_without_fictitious_serialization(self):
        h={'resources':{'r':2},'sites':{'S':{'words':8}},'nets':{}}
        tasks=[{'id':str(i),'bindings':[binding('b','r',n)]} for i,n in enumerate((5,7,3))]
        p=search(tasks,h,width=8);r=profile(tasks,h,p)
        self.assertEqual(r['selected_order_relaxed_lower_bound'],p['makespan'])
        self.assertEqual(r['execution_units'],3)

    def test_actual_materialized_offsets_and_compound_lease_scope(self):
        from test_materialized_tiles import TestMaterializedTiles
        ir=TestMaterializedTiles().fixture(columns=11)
        for task in ir['tasks']:
            selected=[b for b in task['bindings'] if 'materialized_tile' in b]
            if selected:task['bindings']=selected
        p=search(ir['tasks'],ir['hardware'],width=8)
        r=profile(ir['tasks'],ir['hardware'],p)
        self.assertLessEqual(r['selected_order_relaxed_lower_bound'],p['makespan'])
        self.assertGreater(r['event_vertices'],4*r['execution_units'])
        from test_phased_compounds import example,candidate
        ir=example(columns=9)
        task=next(t for t in ir['tasks'] if t['id']=='v');task['bindings']=[candidate(ir)]
        p=search(ir['tasks'],ir['hardware'],width=8);r=profile(ir['tasks'],ir['hardware'],p)
        self.assertEqual(r['execution_units'],len(ir['tasks']))
        self.assertLessEqual(r['selected_order_relaxed_lower_bound'],p['makespan'])


if __name__=='__main__':unittest.main()
