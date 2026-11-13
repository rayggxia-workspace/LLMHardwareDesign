from copy import deepcopy
import random
import unittest
from types import SimpleNamespace

from cover_frontier import catalogue,search
from loop_dp import search as atomic_search
from test_loop_dp import binding
from transition import evaluate_transition,retention_actions
from verify_cover_frontier import verify


class TestCoverFrontier(unittest.TestCase):
    def test_against_independent_exhaustion_with_overlapping_covers(self):
        # Native atomic and cover services use the same explicit action pool.
        # No planner/catalogue/verifier code constructs this reference optimum.
        for seed in range(60):
            rng=random.Random(seed)
            h={'resources':{'r0':1,'r1':1},'sites':{'S':{'words':8}},
               'nets':{n:{'cost':1} for n in 'abc'},'incompatible_nets':[['a','b']]}
            tasks=[{'id':str(i),'after':[str(j) for j in range(i) if rng.random()<.4],
                    'bindings':[binding(str(k),'r'+str(rng.randrange(2)),rng.randint(1,6),[rng.choice('abc')])
                                for k in range(2)]} for i in range(4)]
            covers=[{'id':'f'+str(i),'covers':[str(i),str(i+1)],
                'bindings':[binding('f','r'+str(rng.randrange(2)),rng.randint(1,9),[rng.choice('abc')])]}
                for i in range(3)]
            choices=[{'covers':[t['id']],'bindings':t['bindings']} for t in tasks]+covers;best=[]
            def enumerate_all(done,ends,resources,nets,traffic):
                if len(done)==4:
                    best.append((max(ends.values()),traffic,len(nets)));return
                for action in choices:
                    members=set(action['covers']);ps=set().union(*(set(tasks[int(n)]['after']) for n in members))-members
                    if members&done or not ps<=done:continue
                    for b in action['bindings']:
                        union=nets|set(b['nets'])
                        if {'a','b'}<=union or len(union)>2:continue
                        r=b['resources'][0];end=max([resources[r]]+[ends[n] for n in ps])+b['ticks']
                        enumerate_all(done|members,{**ends,**dict.fromkeys(members,end)},
                            {**resources,r:end},union,traffic+2)
            enumerate_all(set(),{},dict(r0=0,r1=0),set(),0)
            result=search(tasks,h,covers,width=None,ready_limit=None,wire_budget=2)
            if best:
                self.assertEqual((result['makespan'],result['external_words'],result['wire_cost']),min(best),seed)
                self.assertTrue(verify(tasks,h,covers,result,2)['passed'])
            else:self.assertEqual(result['status'],'no_plan_in_bounded_search',seed)

    def test_different_coverage_lengths_meet_and_keep_atomic_backbone(self):
        h={'resources':{'r':1},'sites':{'S':{'words':8}},'nets':{}}
        tasks=[{'id':str(i),'after':[str(i-1)] if i else [],'bindings':[binding('a','r',10)]}
               for i in range(8)]
        covers=[{'id':'f','covers':[str(i) for i in range(6)],'bindings':[binding('f','r',7)]}]
        old=atomic_search(tasks,h,width=2);result=search(tasks,h,covers,width=2,backbone=old)
        self.assertEqual(result['makespan'],27);self.assertEqual(len(result['tasks']),3)
        self.assertTrue(verify(tasks,h,covers,result)['passed'])
        bad=deepcopy(result);bad['tasks'][0]['covers'].pop()
        with self.assertRaisesRegex(ValueError,'membership'):verify(tasks,h,covers,bad)
        bad=deepcopy(result);bad['tasks'].pop()
        with self.assertRaisesRegex(ValueError,'incomplete'):verify(tasks,h,covers,bad)

    def test_nonconvex_cover_cannot_hide_required_external_work(self):
        tasks=[{'id':str(i),'after':[str(i-1)] if i else [],'bindings':[binding('a','r',1)]}
               for i in range(3)]
        bad=[{'id':'f','covers':['0','2'],'bindings':[binding('f','r',1)]}]
        with self.assertRaisesRegex(ValueError,'nonconvex'):catalogue(tasks,bad)

    def test_resident_loop_invalidates_both_real_private_stores(self):
        h={'resources':{'r':1},'sites':{'M.S':{'words':32},'E.S':{'words':8}},'nets':{}}
        b={**binding('resident','r',10),'site':'M.S','scratch_words':24,
            'scratch_by_site':{'M.S':24,'E.S':3},'resident_region':{
                'kind':'serial-native-resident-loop-v1','invalidate_read_cache':['M.S','E.S']}}
        state=SimpleNamespace(resources={'r':(7,)},cache={'M.S':('x',4,12),'E.S':('y',2,2)},
                              makespan=7,nets=frozenset())
        self.assertEqual(retention_actions(state,b),('invalidate',))
        result=evaluate_transition(state,b,h,3,retention='invalidate')
        self.assertTrue(result['legal']);self.assertEqual(result['cache'],{})
        self.assertEqual(result['start'],7);self.assertEqual(len(state.cache),2)
        self.assertEqual(len(result['details']['discarded_read_cache']),2)
        bad=deepcopy(b);bad['resident_region']['invalidate_read_cache']=['M.S']
        self.assertFalse(evaluate_transition(state,bad,h,3,retention='invalidate')['legal'])

    def test_cached_input_must_reload_after_a_cover_and_checker_catches_false_hit(self):
        h={'resources':{'r':1},'sites':{'M.S':{'words':32},'E.S':{'words':8}},'nets':{}}
        cached={**binding('cache','r',8),'site':'M.S','scratch_words':12,'warm_ticks':1,
            'external_read_words':4,'warm_read_words':1,'read_cache':{
                'site':'M.S','tag':'x','stripe':1,'cache_words':3}}
        native={**binding('original','r',20),'site':'M.S'}
        resident={**binding('resident','r',10),'site':'M.S','scratch_words':24,
            'scratch_by_site':{'M.S':24,'E.S':3},'resident_region':{
                'kind':'serial-native-resident-loop-v1','invalidate_read_cache':['M.S','E.S']}}
        tasks=[{'id':'load','bindings':[cached]},
               {'id':'a','after':['load'],'bindings':[native]},
               {'id':'b','after':['a'],'bindings':[native]},
               {'id':'reuse','after':['b'],'bindings':[cached]}]
        covers=[{'id':'f','covers':['a','b'],'bindings':[resident]}]
        plan=search(tasks,h,covers,width=8);self.assertEqual(plan['makespan'],26)
        self.assertFalse(plan['tasks'][-1]['cache_hit']);self.assertTrue(verify(tasks,h,covers,plan)['passed'])
        again=search(tasks,h,covers,width=8,backbone=plan)
        self.assertEqual(again['makespan'],26);verify(tasks,h,covers,again)
        bad=deepcopy(plan);bad['tasks'][-1]['cache_hit']=True
        with self.assertRaisesRegex(ValueError,'cache hit claim'):verify(tasks,h,covers,bad)
        bad=deepcopy(plan);bad['tasks'][1]['evaluation']['discarded_read_cache']=[]
        with self.assertRaisesRegex(ValueError,'resident loop state'):verify(tasks,h,covers,bad)


if __name__=='__main__':unittest.main()
