from copy import deepcopy
import random
from types import SimpleNamespace
import unittest

from future_resource_tail import FutureResourceTail,PendingSuffix
from loop_dp import search
from net_tail import ConditionalTail
from test_loop_dp import binding
from verify_loop_dp import verify


def context(tasks,h,budget=None):
    children={t['id']:[] for t in tasks}
    for t in tasks:
        for p in t.get('after',[]):children[p].append(t['id'])
    order=[];remaining=set(children)
    while remaining:
        ready=sorted(n for n in remaining if all(c in order for c in children[n]))
        if not ready:raise ValueError('cycle')
        order.extend(ready);remaining-=set(ready)
    fixed=frozenset(n for n,v in h['nets'].items() if v.get('fixed'))
    c=ConditionalTail(tasks,h,children,order,fixed=fixed,
        conflicts=tuple(frozenset(p) for p in h.get('incompatible_nets',[])),wire_budget=budget)
    return FutureResourceTail(c,tasks,h)


def independent_next(tasks,h,state,budget=None):
    # Plain serial append-only reservations. No transition, search or bound
    # function participates in this independent completion oracle.
    for i,t in enumerate(tasks):
        if state.done&(1<<i):continue
        if any(p not in state.frontier for p in t.get('after',[])):continue
        for b in t['bindings']:
            nets=state.nets|frozenset(b['nets'])
            physical=nets|{n for n,v in h['nets'].items() if v.get('fixed')}
            if any(set(p)<=physical for p in h.get('incompatible_nets',[])):continue
            if budget is not None and sum(h['nets'][n]['cost'] for n in nets if not h['nets'][n].get('fixed'))>budget:continue
            end=max([state.frontier[p] for p in t.get('after',[])]+
                    [min(state.resources[r]) for r in b['resources']]+[0])+b['ticks']
            rs=state.resources.copy()
            for r in b['resources']:rs[r]=tuple(sorted(rs[r][1:]+(end,)))
            yield SimpleNamespace(done=state.done|(1<<i),frontier={**state.frontier,t['id']:end},
                resources=rs,nets=nets,makespan=max(state.makespan,end),windows={})


def exhaustive(tasks,h,state,budget=None):
    best=None
    def visit(s):
        nonlocal best
        if best is not None and s.makespan>=best:return
        if s.done==(1<<len(tasks))-1:best=s.makespan;return
        for new in independent_next(tasks,h,s,budget):visit(new)
    visit(state)
    return best


class TestFutureResourceTail(unittest.TestCase):
    def test_pending_suffix_real_task_bits_and_empty_profiles(self):
        rng=random.Random(22120)
        for size in (0,1,7,8,9,65,300):
            rows=[(rng.randrange(100),1<<i) for i in rng.sample(range(1000),size)]
            index=PendingSuffix(rows)
            for _ in range(50):
                done=sum(bit for _,bit in rows if rng.randrange(2))
                self.assertEqual(index.maximum(done),max((v for v,b in rows if not b&done),default=None))
            self.assertIsNone(index.maximum(sum(b for _,b in rows)))

    def test_unready_long_chain_changes_binding_without_new_actions(self):
        h={'resources':{'M0':1,'M1':1,'G':1,'other':1},'sites':{'S':{'words':8}},'nets':{}}
        tasks=[{'id':'A','bindings':[binding('fast','M0',80),binding('alternative','M1',81)]},
            {'id':'D','after':['A'],'bindings':[binding('D','G',30)]},
            {'id':'B','bindings':[binding('B','other',1)]},
            {'id':'C','after':['B'],'bindings':[binding('C','M0',100)]}]
        before=deepcopy((tasks,h))
        old=search(tasks,h,width=1,ready_limit=1,rank_policy='net_resource_tail')
        new=search(tasks,h,width=1,ready_limit=1,rank_policy='net_future_resource_tail')
        self.assertEqual(old['makespan'],180);self.assertEqual(new['makespan'],111)
        self.assertEqual(new['tasks'][0]['binding'],'alternative')
        self.assertGreater(new['future_resource_tail_statistics']['stronger_than_ready_bound'],0)
        self.assertNotIn('future_resource_tail_statistics',old)
        verify(tasks,h,new);self.assertEqual(before,(tasks,h))

    def test_lower_bound_against_exhaustive_dag_completions_and_multislot_prefixes(self):
        rng=random.Random(22121)
        for trial in range(70):
            h={'resources':{'a':rng.randint(1,2),'b':rng.randint(1,2)},'sites':{'S':{'words':8}},
               'nets':{n:{'cost':1,'fixed':n=='x' and trial%7==0} for n in ('x','y','z')},
               'incompatible_nets':[['x','y']] if trial%2 else []}
            budget=2 if trial%3 else None;tasks=[]
            for i in range(rng.randint(2,5)):
                bs=[]
                for j in range(2):
                    b=binding(str(j),rng.choice(['a','b']),rng.randint(1,15),[rng.choice(['x','y','z'])])
                    if rng.random()<.2:b['resources']=['a','b']
                    bs.append(b)
                tasks.append({'id':str(i),'after':[str(j) for j in range(i) if rng.random()<.35],'bindings':bs})
            bound=context(tasks,h,budget)
            resources={r:tuple(sorted(rng.randrange(15) for _ in range(cap))) for r,cap in h['resources'].items()}
            state=SimpleNamespace(done=0,frontier={},resources=resources,nets=frozenset(),
                makespan=max(max(v) for v in resources.values()),windows={})
            for prefix in range(3):
                before=deepcopy(vars(state));best=exhaustive(tasks,h,state,budget);value=bound.get(state)
                if best is not None:self.assertIsNotNone(value);self.assertLessEqual(value,best,(trial,prefix,value,best))
                self.assertEqual(value,bound.get(state));self.assertEqual(vars(state),before)
                children=list(independent_next(tasks,h,state,budget))
                if not children:break
                state=rng.choice(children)

    def test_done_tasks_leave_suffix_index_even_after_frontier_removal(self):
        h={'resources':{'a':1},'sites':{'S':{'words':8}},'nets':{}}
        tasks=[{'id':'a','bindings':[binding('a','a',2)]},
               {'id':'b','after':['a'],'bindings':[binding('b','a',100)]},
               {'id':'c','after':['b'],'bindings':[binding('c','a',1)]}]
        bound=context(tasks,h)
        state=SimpleNamespace(done=3,frontier={'b':102},resources={'a':(102,)},nets=frozenset(),makespan=102,windows={})
        self.assertEqual(bound.get(state),103)
        state.done=7;state.resources={'a':(103,)};state.makespan=103
        self.assertEqual(bound.get(state),103)

    def test_materialized_calendar_offset_profiles_are_not_merged(self):
        h={'resources':{'p':1,'e':1},'sites':{'S':{'words':8}},'nets':{},
           'window_calendar':{'kind':'fixed-offset-calendar-v1','resources':['e']}}
        tasks=[]
        for name,offset in [('a',0),('b',6)]:
            b=binding(name,'p',10);b['resources'].append('e')
            b['materialized_tile']={'resource_offsets':{'e':(offset,offset+4)}}
            tasks.append({'id':name,'bindings':[b]})
        bound=context(tasks,h)
        self.assertEqual(len(bound.groups),2)
        state=SimpleNamespace(done=0,frontier={},resources={'p':(0,),'e':(0,)},nets=frozenset(),
            makespan=12,windows={'e':((0,6),(10,12))})
        # Independently enumerate all integer starts against the existing
        # auxiliary bookings, ignoring future task/task contention.
        completions=[]
        for _,offset in [('a',0),('b',6)]:
            start=next(s for s in range(100) if all(not(s+offset<hi and lo<s+offset+4) for lo,hi in state.windows['e']))
            completions.append(start+10)
        self.assertEqual(bound.get(state),max([state.makespan]+completions))

    def test_ordinary_and_phase_compounds_use_only_registered_barriers(self):
        from test_phased_compounds import example,candidate
        from test_column_shards import initial
        from transition import evaluate_transition
        ir=example(columns=9);task=next(t for t in ir['tasks'] if t['id']=='v')
        phase=candidate(ir)
        ordinary=next(b for b in task['bindings'] if 'parallel_shards' in b and 'phase_execution' not in b)
        for b in (ordinary,phase):
            tasks=[{'id':'v','bindings':[b]}];bound=context(tasks,ir['hardware'])
            state=initial(ir);state.done=0
            # An ordinary compound can start one child before another;
            # the phase protocol explicitly requires the union barrier.
            r=next(iter(b['parallel_shards']['children'][0]['binding']['resources']))
            state.resources[r]=(10000,);state.makespan=10000
            ev=evaluate_transition(state,b,ir['hardware'],0,retention=('preserve',)*len(b['parallel_shards']['children']))
            self.assertLessEqual(bound.get(state),ev['makespan'])
            plan=search(tasks,ir['hardware'],width=8,rank_policy='net_future_resource_tail')
            verify(tasks,ir['hardware'],plan)

    def test_upper_skip_and_integer_arithmetic_match_unsimplified_bound(self):
        rng=random.Random(22122)
        for _ in range(40):
            h={'resources':{'a':2,'b':1},'sites':{'S':{'words':8}},'nets':{}}
            tasks=[{'id':str(i),'bindings':[binding('x','a',rng.randrange(1,100)),
                    binding('y','b',rng.randrange(1,100))]} for i in range(20)]
            bound=context(tasks,h);huge=2**60
            state=SimpleNamespace(done=rng.getrandbits(20),frontier={},resources={'a':(huge,huge+1),'b':(huge+7,)},
                nets=frozenset(),makespan=huge+7,windows={})
            c=bound.conditional;tails=c.get(state.nets)
            expected=max([state.makespan]+[c.ready_finish(t['id'],state.nets,state.resources,0)+
                max((tails[x] for x in c.children[t['id']]),default=0)
                for i,t in enumerate(tasks) if not state.done&(1<<i)])
            self.assertEqual(bound.get(state),expected)


if __name__=='__main__':unittest.main()
