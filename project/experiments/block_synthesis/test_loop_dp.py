from copy import deepcopy
import unittest
import random
from loop_dp import optimize,search
from verify_loop_dp import verify


def binding(name,resource,ticks,nets=()):
    return {'id':name,'site':'S','resources':[resource],'ticks':ticks,'nets':list(nets),
            'scratch_words':2,'external_read_words':1,'external_write_words':1}


class TestLoopDP(unittest.TestCase):
    def test_static_constraints_against_independent_exhaustive_small_dags(self):
        # Exhaust every order/binding on 150 four-node graphs; no solver code
        # or verifier is used to construct the independent optimum.
        for seed in range(150):
            rng=random.Random(seed)
            h={'resources':{'r0':1,'r1':1},'sites':{'S':{'words':8}},
               'nets':{n:{'cost':i+1,'fixed':seed%3==0 and n=='a'} for i,n in enumerate('abcd')},
               'incompatible_nets':[['a','b']]+([['c','d']] if seed%2 else [])}
            tasks=[]
            for i in range(4):
                tasks.append({'id':'t'+str(i),'after':['t'+str(j) for j in range(i) if rng.random()<.4],
                    'bindings':[binding(str(k),'r'+str(rng.randrange(2)),rng.randint(1,4),
                                [rng.choice('abcd')]) for k in range(2)]})
            best=[]
            def enumerate_all(done,times,available,nets):
                if len(done)==4:
                    best.append((max(times.values()),8,sum(h['nets'][n]['cost'] for n in nets if not h['nets'][n]['fixed'])))
                    return
                for t in tasks:
                    if t['id'] in done or not set(t['after'])<=done:continue
                    for b in t['bindings']:
                        chosen=nets|set(b['nets'])
                        physical=chosen|{n for n,v in h['nets'].items() if v['fixed']}
                        if any(all(n in physical for n in pair) for pair in h['incompatible_nets']):continue
                        r=b['resources'][0]
                        end=max([available[r]]+[times[p] for p in t['after']])+b['ticks']
                        enumerate_all(done|{t['id']},{**times,t['id']:end},{**available,r:end},chosen)
            enumerate_all(set(),{},dict(r0=0,r1=0),set())
            result=optimize(tasks,h,width=4096,ready_limit=4)
            if not best:self.assertEqual(result['status'],'no_plan_in_bounded_search',seed)
            else:
                self.assertEqual((result['makespan'],result['external_words'],result['wire_cost']),min(best),seed)
                self.assertTrue(verify(tasks,h,result)['passed'])

    def conflict_case(self):
        h={'resources':{'r':1},'sites':{'S':{'words':8}},
           'nets':{n:{'cost':1} for n in ('a','b','c')},'incompatible_nets':[['a','b']]}
        tasks=[{'id':'first','bindings':[binding('use_a','r',1,['a'])]},
               {'id':'second','after':['first'],'bindings':[
                   binding('conflicting_b','r',1,['b']),binding('legal_c','r',2,['c'])]}]
        return tasks,h

    def test_static_conflict_chooses_slower_legal_binding(self):
        tasks,h=self.conflict_case()
        for width in (1,8):
            result=optimize(tasks,h,width=width)
            self.assertEqual(result['makespan'],3)
            self.assertEqual(result['nets'],['a','c'])
            self.assertGreater(result['search_statistics']['rejected_static_conflicts'],0)
            self.assertTrue(verify(tasks,h,result)['passed'])

    def test_static_conflict_without_alternative_never_succeeds(self):
        tasks,h=self.conflict_case();tasks[1]['bindings']=tasks[1]['bindings'][:1]
        for width in (1,8):
            self.assertEqual(optimize(tasks,h,width=width)['status'],'no_plan_in_bounded_search')

    def test_checker_rejects_foreign_conflicting_plan_despite_serial_time(self):
        tasks,h=self.conflict_case();unchecked=deepcopy(h);unchecked.pop('incompatible_nets')
        bad=optimize(tasks,unchecked,width=8)
        self.assertEqual(bad['nets'],['a','b'])
        self.assertLessEqual(bad['tasks'][0]['end'],bad['tasks'][1]['start'])
        with self.assertRaisesRegex(ValueError,'incompatible static'):verify(tasks,h,bad)

    def test_conflicting_demands_inside_one_binding_are_rejected(self):
        _,h=self.conflict_case()
        tasks=[{'id':'one','bindings':[binding('illegal','r',1,['a','b']),binding('legal','r',2,['c'])]}]
        result=optimize(tasks,h,width=8)
        self.assertEqual(result['nets'],['c']);self.assertTrue(verify(tasks,h,result)['passed'])

    def test_conflict_history_survives_frontier_eviction(self):
        tasks,h=self.conflict_case()
        tasks.insert(1,{'id':'middle','after':['first'],'bindings':[binding('none','r',5)]})
        tasks[2]['after']=['middle']
        result=optimize(tasks,h,width=8)
        self.assertEqual(result['nets'],['a','c']);self.assertEqual(result['makespan'],8)
        self.assertTrue(verify(tasks,h,result)['passed'])

    def test_fixed_connection_conflicts_even_without_a_task_user(self):
        _,h=self.conflict_case();h['nets']['a']['fixed']=True
        tasks=[{'id':'one','bindings':[binding('illegal','r',1,['b']),binding('legal','r',2,['c'])]}]
        result=optimize(tasks,h,width=8)
        self.assertEqual(result['nets'],['c']);verify(tasks,h,result)
        plain=deepcopy(h);plain.pop('incompatible_nets')
        with self.assertRaisesRegex(ValueError,'incompatible static'):verify(tasks,h,optimize(tasks,plain,width=8))

    def test_malformed_conflicts_and_impossible_fixed_base_fail_closed(self):
        tasks,h=self.conflict_case()
        plan=optimize(tasks,h,width=8)
        for pair in (['a','missing'],['a'],['a','b','c'],['a','a']):
            bad=deepcopy(h);bad['incompatible_nets']=[pair]
            with self.assertRaises(ValueError):search(tasks,bad)
            with self.assertRaises(ValueError):verify(tasks,bad,plan)
        h['nets']['a']['fixed']=True;h['nets']['b']['fixed']=True
        with self.assertRaisesRegex(ValueError,'fixed static'):search(tasks,h)
        with self.assertRaisesRegex(ValueError,'incompatible static'):verify(tasks,h,plan)

    def test_frontier_explores_order_and_binding_and_improves_greedy(self):
        h={'resources':{'r0':1,'r1':1,'r2':1},'sites':{'S':{'words':8}},'nets':{}}
        tasks=[{'id':'A','bindings':[binding('a0','r0',3),binding('a1','r1',4)]},
               {'id':'B','bindings':[binding('b0','r0',3)]},
               {'id':'C','after':['A','B'],'bindings':[binding('c','r2',1)]}]
        result=optimize(tasks,h,width=4)
        self.assertEqual(result['baseline']['makespan'],7)
        self.assertEqual(result['makespan'],5)
        self.assertTrue(verify(tasks,h,result)['passed'])

    def test_static_net_history_survives_until_future_reuse(self):
        h={'resources':{'r0':1},'sites':{'S':{'words':8}},
           'nets':{'A':{'cost':1},'B':{'cost':2}}}
        tasks=[{'id':'first','bindings':[binding('a','r0',1,['A']),binding('b','r0',1,['B'])]},
               {'id':'later-layer','after':['first'],'bindings':[binding('c','r0',1,['B'])]}]
        result=optimize(tasks,h,width=2)
        self.assertEqual(result['wire_cost'],2)
        self.assertEqual(result['baseline']['wire_cost'],3)
        self.assertTrue(verify(tasks,h,result)['passed'])
        limited=optimize(tasks,h,width=2,wire_budget=2)
        self.assertEqual(limited['status'],'planned')
        self.assertNotEqual(limited['baseline']['status'],'planned')
        self.assertTrue(verify(tasks,h,limited,2)['passed'])

    def test_independent_checker_rejects_overlap_and_unknown_binding(self):
        h={'resources':{'r':1},'sites':{'S':{'words':8}},'nets':{}}
        tasks=[{'id':name,'bindings':[binding(name,'r',3)]} for name in ('A','B')]
        result=optimize(tasks,h,width=2);verify(tasks,h,result)
        bad=deepcopy(result);bad['tasks'][1]['start']=0;bad['tasks'][1]['end']=3
        with self.assertRaises(ValueError):verify(tasks,h,bad)
        bad=deepcopy(result);bad['tasks'][0]['binding']='invented'
        with self.assertRaises(ValueError):verify(tasks,h,bad)


if __name__=='__main__':unittest.main()
