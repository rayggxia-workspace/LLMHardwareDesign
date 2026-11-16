import random
import unittest

from static_wiring import completion_covers,can_complete


class TestStaticWiring(unittest.TestCase):
    def test_all_frontiers_against_exhaustive_physical_unions(self):
        for seed in range(100):
            rng=random.Random(seed);names=list('abcdef')
            h={'nets':{n:{'cost':rng.randrange(4),'fixed':rng.random()<.1} for n in names},
               'incompatible_nets':[['a','b']]+([['c','d']] if seed%2 else [])}
            tasks=[{'bindings':[{'nets':rng.sample(names,rng.randrange(4))} for _ in range(3)]}
                   for _ in range(3)]
            budget=rng.randrange(10);covers=completion_covers(tasks,h,wire_budget=budget)
            self.assertIsNotNone(covers)
            fixed={n for n in names if h['nets'][n]['fixed']}
            legal=[]
            # Exhaust all final metal unions, independent of the cover code.
            for mask in range(1<<len(names)):
                union={n for i,n in enumerate(names) if mask>>i&1}|fixed
                if sum(h['nets'][n]['cost'] for n in union-fixed)>budget:continue
                if any(set(pair)<=union for pair in h['incompatible_nets']):continue
                if all(any(set(b['nets'])<=union for b in t['bindings']) for t in tasks):legal.append(union)
            for mask in range(1<<len(names)):
                frontier=frozenset(n for i,n in enumerate(names) if mask>>i&1)
                self.assertEqual(can_complete(frontier,h,covers,budget),any(frontier<=u for u in legal),
                                 (seed,mask))

    def test_cutoff_falls_back_without_false_infeasibility(self):
        h={'nets':{'a':{'cost':1},'b':{'cost':1}}}
        tasks=[{'bindings':[{'nets':['a']},{'nets':['b']}]}]
        self.assertIsNone(completion_covers(tasks,h,wire_budget=1,limit=1))
        self.assertTrue(can_complete(frozenset(),h,None,1))
        self.assertIsNone(completion_covers(tasks,h,wire_budget=None))

    def test_completed_tasks_do_not_lose_their_static_wires(self):
        h={'nets':{'a':{'cost':1},'b':{'cost':1},'n':{'cost':1}}}
        tasks=[{'bindings':[{'nets':['a']},{'nets':['b']}]},{'bindings':[{'nets':['n','b']}]}]
        covers=completion_covers(tasks,h,wire_budget=2)
        self.assertEqual(covers,(frozenset(['b','n']),))
        self.assertFalse(can_complete(frozenset(['a']),h,covers,2))
        self.assertTrue(can_complete(frozenset(['b']),h,covers,2))


if __name__=='__main__':unittest.main()
