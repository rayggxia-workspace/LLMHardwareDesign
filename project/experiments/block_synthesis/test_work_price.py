from copy import deepcopy
import random
from types import SimpleNamespace
import unittest

from loop_dp import search
from net_tail import ConditionalTail
from test_tile_bindings import fixture,variants_for
from verify_loop_dp import verify
from work_price import WorkPriceBound


def bound_for(tasks,capacities,*,conflicts=()):
    nets={n:{'cost':1,'fixed':False} for t in tasks for b in t['bindings'] for n in b['nets']}
    h={'resources':capacities,'nets':nets}
    ctx=ConditionalTail(tasks,h,{t['id']:[] for t in tasks},[t['id'] for t in reversed(tasks)],conflicts=conflicts)
    return WorkPriceBound(ctx,tasks,h),h


def exhaustive(tasks,state):
    best=None
    def visit(done,calendar,finish):
        nonlocal best
        if best is not None and finish>=best:return
        if done==(1<<len(tasks))-1:best=finish;return
        for i,t in enumerate(tasks):
            if done&(1<<i):continue
            for b in t['bindings']:
                end=max((min(calendar[r]) for r in b['resources']),default=0)+b['ticks']
                updated=calendar.copy()
                for r in b['resources']:updated[r]=tuple(sorted(updated[r][1:]+(end,)))
                visit(done|(1<<i),updated,max(finish,end))
    visit(state.done,state.resources,state.makespan)
    return best


class TestWorkPrice(unittest.TestCase):
    def test_every_price_bound_under_independent_exhaustive_completions(self):
        rng=random.Random(22082)
        for trial in range(36):
            capacities={'a':rng.randint(1,2),'b':rng.randint(1,2)}
            tasks=[]
            for i in range(rng.randint(2,5)):
                bindings=[]
                for j in range(2):
                    rs=rng.choice([['a'],['b'],['a','b']]);ticks=rng.randint(1,15)
                    bindings.append({'id':str(j),'resources':rs,'nets':[],'ticks':ticks})
                tasks.append({'id':str(i),'bindings':bindings})
            work,h=bound_for(tasks,capacities)
            calendar={r:tuple(sorted(rng.randint(0,13) for _ in range(n))) for r,n in capacities.items()}
            done=rng.randrange(1<<len(tasks))
            state=SimpleNamespace(done=done,resources=calendar,nets=frozenset(),makespan=max(max(v) for v in calendar.values()))
            before=deepcopy(state);value=work.get(state)
            self.assertLessEqual(value,exhaustive(tasks,state),(trial,value))
            self.assertEqual(before.__dict__,state.__dict__)
            self.assertEqual(value,work.get(state))

    def test_calendar_state_large_integer_and_static_union_change_the_bound(self):
        tasks=[{'id':str(i),'bindings':[{'resources':['a'],'nets':['x'],'ticks':10},
             {'resources':['b'],'nets':['y'],'ticks':100}]} for i in range(4)]
        bound,h=bound_for(tasks,{'a':1,'b':1},conflicts=[frozenset({'y','blocked'})])
        h['nets']['blocked']={'cost':1,'fixed':False}
        free=SimpleNamespace(done=0,resources={'a':(0,),'b':(0,)},nets=frozenset(),makespan=0)
        busy=deepcopy(free);busy.resources['a']=(100,);busy.makespan=100
        self.assertGreater(bound.get(busy),bound.get(free))
        restricted=deepcopy(free);restricted.nets=frozenset({'blocked'})
        self.assertGreaterEqual(bound.get(restricted),bound.get(free))
        huge=[{'id':'huge','bindings':[{'resources':['a'],'nets':[],'ticks':2**60+7}]}]
        exact,_=bound_for(huge,{'a':1})
        self.assertEqual(exact.get(SimpleNamespace(done=0,resources={'a':(0,)},nets=frozenset(),makespan=0)),2**60+7)

    def test_same_pool_plan_checked_and_compound_relaxations_remain_legal(self):
        ir,q=fixture(columns=11);variants_for(ir,q)
        for width in (1,8):
            plan=search(ir['tasks'],ir['hardware'],width=width,rank_policy='net_work_price',wire_budget=12)
            self.assertEqual(plan['status'],'planned')
            verify(ir['tasks'],ir['hardware'],plan,wire_budget=12)
            self.assertGreater(plan['work_price_statistics']['prices'],0)
        with self.assertRaises(ValueError):search(ir['tasks'],ir['hardware'],rank_policy='net_work_price',work_price_rounds=0)


if __name__=='__main__':unittest.main()
