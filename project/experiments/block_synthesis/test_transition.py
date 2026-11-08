from copy import deepcopy
import random
import unittest
import numpy as np

from test_dot_cache import example
from memory import descriptor_ticks
from loop_dp import State, search
from transition import evaluate_transition
from verify_loop_dp import verify
from dot_cache_replay import DotCache


def upgraded():
    ir = example()
    for b in ir['tasks'][0]['bindings']:
        c = b.get('read_cache')
        if c:
            c.update(cost_model='dot-prefix-state-v2', load_ticks=descriptor_ticks(
                ir['hardware']['virtual_memory'], 1, 'load', 3))
    return ir


class TestTransition(unittest.TestCase):
    def test_partial_hit_counts_and_purity(self):
        ir=upgraded();h=ir['hardware']
        b=next(b for b in ir['tasks'][0]['bindings'] if b.get('read_cache',{}).get('stripe')==2)
        c=b['read_cache']
        for q in (0,1,2,4):
            s=State(0,{}, {r:(0,)*n for r,n in h['resources'].items()},frozenset(),0,0,(),{})
            if q:s.cache[c['site']]=(c['tag'],q,6*q)
            before=deepcopy(s)
            e=evaluate_transition(s,b,h,0,retention='preserve')
            self.assertTrue(e['legal']);self.assertEqual(s,before)
            self.assertEqual(e['details']['reused_prefix'],min(q,2))
            self.assertEqual(e['traffic'],b['external_read_words']+b['external_write_words']-6*min(q,2))
            self.assertEqual(e['cache'][c['site']][1],max(q,2))

    def test_scalar_record_oracle_partial_prefix(self):
        rng=random.Random(220)
        for _ in range(80):
            R,N,K=[rng.randint(1,6) for _ in range(3)]
            a,b=rng.choice((1,3)),rng.choice((1,3));t=rng.randint(0,K);q=rng.randint(0,K)
            resident={(r,j,k) for r in range(R) for j in range(min(q,t)) for k in range(a)}
            reads=0;zero=False
            for r in range(R):
                for col in range(N):
                    for j in range(K):
                        staging=set()
                        for x in range(a):
                            for y in range(b):
                                key=(r,j,x)
                                if key not in resident:
                                    reads+=1
                                    if j<t:resident.add(key)
                                if y not in staging:reads+=1;staging.add(y)
                                if not zero:reads+=1;zero=True
            self.assertEqual(reads,R*a*(t-min(q,t))+R*N*a*b*(K-t)+R*N*K*b+1)

    def test_independent_checker_and_finite_sram_replay(self):
        ir=upgraded();original=ir['tasks'][0];tasks=[]
        for i,t in enumerate((1,2,1,2)):
            b=deepcopy(next(b for b in original['bindings'] if b.get('read_cache',{}).get('stripe')==t))
            b['read_cache']['primitive']='v'+str(i)
            tasks.append({'id':'task'+str(i),'after':['task'+str(i-1)] if i else [],'bindings':[b]})
        ir['tasks']=tasks
        p=search(tasks,ir['hardware'],width=16)
        verify(tasks,ir['hardware'],p)
        self.assertEqual(p['tasks'][1]['evaluation']['reused_prefix'],1)
        cache=DotCache(ir,p);a=np.arange(10,dtype=np.int64).reshape(2,5)-(1<<24)
        b=np.arange(15,dtype=np.int64).reshape(5,3)
        for i in range(4):
            node=deepcopy(ir['primitive_program']['instructions'][0]);node.update(kernel='task'+str(i),id='v'+str(i))
            self.assertTrue(np.array_equal(cache.dot(node,a,b),a@b))
        cache.report()
        for field in ('reused_prefix','external_read_words','retained_prefix'):
            bad=deepcopy(p);bad['tasks'][1]['evaluation'][field]+=1
            with self.assertRaises(ValueError):verify(tasks,ir['hardware'],bad)

    def test_wrong_identity_capacity_and_discard(self):
        ir=upgraded();h=ir['hardware'];b=next(b for b in ir['tasks'][0]['bindings'] if b.get('read_cache',{}).get('stripe')==2);c=b['read_cache']
        s=State(0,{}, {r:(0,)*n for r,n in h['resources'].items()},frozenset(),100,0,(),{c['site']:('other',4,24)})
        e=evaluate_transition(s,b,h,0,retention='preserve')
        self.assertEqual(e['details']['reused_prefix'],0)
        self.assertEqual(e['delta_makespan'],max(100,e['end'])-100)
        s.cache[c['site']]=(c['tag'],10,60)
        self.assertFalse(evaluate_transition(s,b,h,0,retention='preserve')['legal'])
        for policy in ('shrink','discard'):
            self.assertTrue(evaluate_transition(s,b,h,0,retention=policy)['legal'])

    def test_each_retention_policy_replayed_and_rechecked(self):
        for policy,expected in (('preserve',4),('shrink',1),('discard',0)):
            ir=upgraded();original=ir['tasks'][0];h=ir['hardware'];tasks=[]
            s=State(0,{}, {r:(0,)*n for r,n in h['resources'].items()},frozenset(),0,0,(),{})
            rows=[];traffic=0
            for i,(t,keep) in enumerate(((4,'preserve'),(1,policy),(4,'preserve'))):
                b=deepcopy(next(b for b in original['bindings'] if b.get('read_cache',{}).get('stripe')==t))
                b['read_cache']['primitive']='v'+str(i)
                task={'id':'task'+str(i),'after':['task'+str(i-1)] if i else [],'bindings':[b]};tasks.append(task)
                ev=evaluate_transition(s,b,h,s.makespan,retention=keep)
                self.assertTrue(ev['legal'])
                if i==2:self.assertEqual(ev['details']['reused_prefix'],expected)
                rows.append({'id':task['id'],'binding':b['id'],'site':b['site'],'start':ev['start'],
                    'end':ev['end'],'cache_hit':ev['cache_hit'],'evaluation':ev['details']})
                traffic+=ev['traffic'];s=State(0,{},ev['resources'],ev['nets'],ev['makespan'],traffic,(),ev['cache'])
            plan={'status':'planned','tasks':rows,'nets':sorted(s.nets),'wire_cost':sum(h['nets'][n]['cost'] for n in s.nets),
                'external_words':traffic,'makespan':s.makespan}
            verify(tasks,h,plan);ir['tasks']=tasks;cache=DotCache(ir,plan)
            a=np.arange(10,dtype=np.int64).reshape(2,5)-(1<<24);b=np.ones((5,3),dtype=np.int64)
            for i in range(3):
                node=deepcopy(ir['primitive_program']['instructions'][0]);node.update(kernel='task'+str(i),id='v'+str(i))
                self.assertTrue(np.array_equal(cache.dot(node,a,b),a@b))


if __name__=='__main__':unittest.main()
