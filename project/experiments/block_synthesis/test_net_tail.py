from copy import deepcopy
import random
import unittest

from loop_dp import search
from net_tail import ConditionalTail
from verify_loop_dp import verify


def binding(name,ticks,nets):
    return {'id':name,'site':'S','resources':['r'],'nets':nets,'ticks':ticks,'scratch_words':1,
            'external_read_words':0,'external_write_words':0}


class TestConditionalTail(unittest.TestCase):
    def test_actual_static_union_changes_future_parallelism_value(self):
        h={'sites':{'S':{'words':8}},'resources':{'r':1},
           'nets':{n:{'cost':1} for n in ('cheap-now','reusable','wide')}}
        tasks=[{'id':'first','bindings':[binding('cheap',1,['cheap-now']),binding('reuse',2,['reusable'])]},
               {'id':'later','after':['first'],'bindings':[binding('fast',2,['reusable','wide']),binding('slow',10,['cheap-now'])]}]
        old=search(tasks,h,width=1,wire_budget=2)
        new=search(tasks,h,width=1,wire_budget=2,rank_policy='net_conditioned_tail')
        self.assertEqual(old['makespan'],11);self.assertEqual(new['makespan'],4)
        verify(tasks,h,new,wire_budget=2)
        self.assertEqual(new['tasks'][0]['binding'],'reuse')

    def test_relaxed_tail_matches_independent_enumeration(self):
        for seed in range(60):
            rng=random.Random(seed);names=['a','b','c','d']
            h={'nets':{n:{'cost':rng.randint(1,3)} for n in names}}
            tasks=[];children={str(i):[] for i in range(4)}
            for i in range(4):
                ps=[str(j) for j in range(i) if rng.randrange(2)]
                for p in ps:children[p].append(str(i))
                tasks.append({'id':str(i),'after':ps,'bindings':[
                    binding(str(j),rng.randint(1,12),rng.sample(names,rng.randint(1,2))) for j in range(3)]})
            budget=rng.randint(3,8);selected=frozenset(rng.sample(names,rng.randint(0,2)))
            tails=ConditionalTail(tasks,h,children,['3','2','1','0'],wire_budget=budget)
            actual=tails.get(selected);expected={}
            for task in reversed(tasks):
                options=[b['ticks'] for b in task['bindings'] if sum(h['nets'][n]['cost'] for n in selected|set(b['nets']))<=budget]
                follow=[expected[n] for n in children[task['id']]]
                expected[task['id']]=min(options)+max(follow,default=0) if options and None not in follow else None
            self.assertEqual(actual,expected,seed)
            self.assertIs(tails.get(selected),actual)

    def test_static_conflict_and_fixed_prelinks_are_not_time_shared(self):
        h={'nets':{'fixed':{'cost':9,'fixed':True},'x':{'cost':2},'y':{'cost':2}}}
        tasks=[{'id':'a','bindings':[binding('x',1,['x']),binding('y',5,['y'])]}]
        tail=ConditionalTail(tasks,h,{'a':[]},['a'],fixed=frozenset(['fixed']),
            conflicts=[frozenset(['fixed','x'])],wire_budget=2)
        self.assertEqual(tail.get(frozenset())['a'],5)
        self.assertIsNone(tail.get(frozenset(['x']))['a'])

    def test_committed_resource_release_is_visible_to_the_next_ready_task(self):
        h={'nets':{},'resources':{'M0':1,'M1':1,'G':1},'sites':{'S':{'words':8}}}
        def b(name,ticks,resource):return {**binding(name,ticks,[]),'resources':[resource]}
        tasks=[{'id':'a','bindings':[b('fast',5,'M0'),b('parallel',6,'M1')]},
               {'id':'b','bindings':[b('only',10,'M0')]},
               {'id':'c','after':['a'],'bindings':[b('tail',3,'G')]}]
        old=search(tasks,h,width=1,rank_policy='net_conditioned_tail')
        new=search(tasks,h,width=1,rank_policy='net_resource_tail')
        self.assertEqual(old['makespan'],15);self.assertEqual(new['makespan'],10)
        verify(tasks,h,new)

    def test_ready_bound_does_not_invent_a_barrier_for_serial_children(self):
        from test_column_shards import fixture,initial,compound
        from phased_compounds import variants_for
        from transition import evaluate_transition
        for phased in (False,True):
            ir=fixture(shared=True)
            if phased:variants_for(ir)
            task=next(t for t in ir['tasks'] if t['id']=='v')
            if phased:task['bindings']=[b for b in task['bindings'] if 'phase_execution' in b]
            else:task['bindings']=[compound(ir)]
            tail=ConditionalTail([task],ir['hardware'],{'v':[]},['v'])
            s=initial(ir)
            private=next(r for r in task['bindings'][0]['parallel_shards']['children'][1]['binding']['resources'] if r.endswith('.M'))
            s.resources[private]=(100000,)
            for b in task['bindings']:
                ev=evaluate_transition(s,b,ir['hardware'],0,retention=('preserve','preserve'))
                self.assertLessEqual(tail.ready_finish('v',s.nets,s.resources,0),ev['end'])


if __name__=='__main__':unittest.main()
