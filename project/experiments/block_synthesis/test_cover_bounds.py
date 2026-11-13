from functools import lru_cache
import random
from types import SimpleNamespace
import unittest

from cover_bounds import Completion
from cover_frontier import catalogue,search
from test_loop_dp import binding
from verify_cover_frontier import verify


class TestCoverBounds(unittest.TestCase):
    def test_bound_on_independently_enumerated_reachable_frontiers(self):
        checked=0
        for seed in range(35):
            rng=random.Random(220150+seed)
            h={'resources':{'r0':1,'r1':1},'sites':{'S':{'words':8}},
               'nets':{n:{'cost':1} for n in 'abc'},'incompatible_nets':[['a','b']]}
            tasks=[{'id':str(i),'after':[str(j) for j in range(i) if rng.random()<.4],
                'bindings':[binding(str(k),'r'+str(rng.randrange(2)),rng.randint(1,7),[rng.choice('abc')])
                            for k in range(2)]} for i in range(4)]
            covers=[{'id':'f'+str(i),'covers':[str(i),str(i+1)],
                'bindings':[binding('f','r'+str(rng.randrange(2)),rng.randint(1,10),[rng.choice('abc')])]}
                for i in range(3)]
            actions,_,_=catalogue(tasks,covers);bound=Completion(actions,h,{str(i):i for i in range(4)},wire_budget=2)
            resource_bound=Completion(actions,h,{str(i):i for i in range(4)},wire_budget=2,resource_releases=True)
            options=[([i],tasks[i]['bindings']) for i in range(4)]
            options += [([i,i+1],covers[i]['bindings']) for i in range(3)]
            states={}
            @lru_cache(None)
            def exact(done,ends,available,nets):
                result=float('inf')
                if done==15:return max(ends)
                for members,bindings in options:
                    mask=sum(1<<i for i in members)
                    ps={int(p) for i in members for p in tasks[i]['after']}-set(members)
                    if done&mask or any(not done&(1<<p) for p in ps):continue
                    for b in bindings:
                        union=tuple(sorted(set(nets)|set(b['nets'])))
                        if {'a','b'}<=set(union) or len(union)>2:continue
                        r=int(b['resources'][0][-1]);end=max([available[r]]+[ends[p] for p in ps])+b['ticks']
                        newends=list(ends);newavailable=list(available)
                        for i in members:newends[i]=end
                        newavailable[r]=end
                        result=min(result,exact(done|mask,tuple(newends),tuple(newavailable),union))
                states[(done,ends,available,nets)]=result
                return result
            optimum=exact(0,(0,)*4,(0,0),())
            for (done,ends,available,nets),opt in states.items():
                frontier={str(i):ends[i] for i in range(4) if done&(1<<i) and any(
                    str(i) in tasks[j]['after'] and not done&(1<<j) for j in range(4))}
                state=SimpleNamespace(done=done,frontier=frontier,nets=frozenset(nets),makespan=max(ends),
                    resources={'r0':(available[0],),'r1':(available[1],)})
                self.assertLessEqual(bound.get(state),opt,(seed,done,ends,available,nets));checked+=1
                self.assertLessEqual(resource_bound.get(state),opt,(seed,done,ends,available,nets))
                self.assertGreaterEqual(resource_bound.get(state),bound.get(state))
            proposed=search(tasks,h,covers,width=None,ready_limit=None,wire_budget=2,rank_policy='hypergraph_completion')
            if optimum<float('inf'):
                self.assertEqual(proposed['makespan'],optimum);verify(tasks,h,covers,proposed,2)
        self.assertGreater(checked,1000)

    def test_whole_service_boundary_is_stronger_than_equal_shares(self):
        h={'resources':{'r':1},'sites':{'S':{'words':8}},'nets':{}}
        tasks=[{'id':n,'after':[] if n!='c' else ['a','b'],'bindings':[binding('a','r',100)]} for n in 'abc']
        covers=[{'id':'f','covers':['a','b'],'bindings':[binding('f','r',10)]}]
        actions,_,_=catalogue(tasks,covers);b=Completion(actions,h,dict(a=0,b=1,c=2))
        state=SimpleNamespace(done=0,frontier={},nets=frozenset(),makespan=0)
        self.assertEqual(b.get(state),110)
        self.assertGreater(b.get(state),5+100)


if __name__=='__main__':unittest.main()
