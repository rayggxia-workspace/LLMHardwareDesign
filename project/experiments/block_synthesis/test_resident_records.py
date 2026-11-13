from copy import deepcopy
from itertools import combinations
import random
import unittest

from native_pointwise import execute,lower
from resident_records import State,plan
from resident_bounds import FutureCopies
from resident_replay import replay
import test_native_pointwise as pointwise_fixture


def powerset(values):
    values=tuple(sorted(values))
    return (frozenset(c) for r in range(len(values)+1) for c in combinations(values,r))


def exhaustive_e(graph,capacity,load,store,*,start=0,initial=None):
    """Set-based cache enumeration, independent of slot/event transitions."""
    produced={n['output'] for n in graph['operations']};live=set(graph['live_out'].values())
    last={}
    for i,n in enumerate(graph['operations']):
        for x in n['inputs']:last[x]=i
    states={(frozenset(),frozenset()) if initial is None else initial:0}
    for i,n in enumerate(graph['operations'][start:],start):
        future={x for x,j in last.items() if j>i}|live;needed=set(n['inputs']);new={}
        for (cache,backed),cost in states.items():
            for before in powerset(cache|needed):
                if not needed<=before or len(before)>capacity:continue
                if any(x in produced and x not in backed for x in before-cache):continue
                spills=(cache-before)&future&produced-backed
                b1=backed|spills;base=cost+len(before-cache)*load+len(spills)*store
                for after in powerset(before|{n['output']}):
                    if n['output'] not in after or len(after)>capacity:continue
                    writes=(before-after)&future&produced-b1
                    key=(after&future,(b1|writes)&future);value=base+len(writes)*store
                    if key not in new or value<new[key]:new[key]=value
        states=new
    return min(cost+len(live-backed)*store for (_,backed),cost in states.items())


def e_graph(pairs,live):
    objects={};ops=[]
    for i,inputs in enumerate(pairs):
        key='n'+str(i)
        for name in inputs:objects.setdefault(name,{'kind':'external','tensor':name,'index':0,'bits':32})
        objects[key]={'kind':'produced','producer':key};ops.append({'id':key,'kind':'E','inputs':list(inputs),
            'output':key,'opcode':5,'shift':0})
    for i,o in enumerate(objects.values()):o['external_address']=100+i
    return {'objects':objects,'operations':ops,'live_out':{x:x for x in live},
            'primitive_outputs':{n['output']:n['output'] for n in ops}}


class TestResidentRecords(unittest.TestCase):
    def test_future_copy_bound_against_independent_exact_suffixes(self):
        rng=random.Random(220143);checked=0
        for _ in range(12):
            pairs=[];available=['a','b','c']
            for i in range(4):
                pairs.append(tuple(rng.choice(available) for _ in range(2)));available.append('n'+str(i))
            g=e_graph(pairs,{'n3',rng.choice(available[3:])});capacity=rng.choice((2,3))
            actors={'E':{'kind':'E','words':capacity,'stride':1,'load_ticks':3,'store_ticks':5}}
            bound=FutureCopies(g,actors)
            for cut in range(5):
                produced={'n'+str(i) for i in range(cut)}
                needed={x for n in g['operations'][cut:] for x in n['inputs']}|set(g['live_out'].values())
                needed&=produced
                for _ in range(20):
                    cache=frozenset(rng.sample(sorted({'a','b','c'}|produced),rng.randrange(capacity+1)))
                    backed=frozenset(x for x in produced if rng.randrange(2))
                    if not needed<=cache|backed:continue
                    row=tuple(sorted(cache))+(None,)*(capacity-len(cache))
                    s=State((row,),backed,(frozenset(),),(None,))
                    exact=exhaustive_e(g,capacity,3,5,start=cut,initial=(cache,backed))
                    estimate=bound.bound(s,cut)
                    self.assertLessEqual(estimate,exact,(pairs,cut,cache,backed,estimate,exact));checked+=1
            for width in (None,1,8):
                result=plan(g,actors,0,width=width,rank_policy='future_copies')
                self.assertGreater(result['bound_calls'],0)
                if width is None:self.assertEqual(result['copy_ticks'],exhaustive_e(g,capacity,3,5))
                replay(g,result,{(o['tensor'],0):1 for o in g['objects'].values() if o['kind']=='external'})
        self.assertGreater(checked,500)

    def test_exhaustive_small_dataflows_and_independent_finite_s_replay(self):
        rng=random.Random(220141)
        for _ in range(40):
            pairs=[];available=['a','b','c','d']
            for i in range(5):
                pairs.append(tuple(rng.choice(available) for _ in range(2)));available.append('n'+str(i))
            g=e_graph(pairs,{'n4',rng.choice(available[4:])})
            capacity=rng.choice((2,3,4));actors={'E':{'kind':'E','words':capacity,'stride':1,'load_ticks':3,'store_ticks':5}}
            result=plan(g,actors,0,width=None)
            self.assertEqual(result['copy_ticks'],exhaustive_e(g,capacity,3,5))
            values={(o['tensor'],0):rng.randrange(-32768,32768) for o in g['objects'].values() if o['kind']=='external'}
            r=replay(g,result,values);gold=execute(g,values)
            self.assertEqual(r['observed_native_outputs'],{n['output']:gold[n['output']] for n in g['operations']})

    def test_real_pointwise_recipes_dirty_remote_stores_padding_and_b_reuse(self):
        p=pointwise_fixture.TestNativePointwise().program();g=lower(p,[n['id'] for n in p['instructions']])
        for i,o in enumerate(g['objects'].values()):o['external_address']=100+i
        actors={'P':{'kind':'M','words':32,'stride':8,'load_ticks':3,'store_ticks':5},
                'U':{'kind':'E','words':3,'stride':1,'load_ticks':4,'store_ticks':6}}
        values={('x',0):-2147483648,('y',0):2147483647};gold=execute(g,values)
        dp=plan(g,actors,0,width=8);baseline=plan(g,actors,0,width=1,spill_all=True)
        self.assertLess(dp['external_words'],baseline['external_words'])
        self.assertTrue(any(e['op']=='M_TERM' and e['reuse_b'] for e in dp['events']))
        self.assertTrue(any(e['op']=='LOAD_ZERO' for e in dp['events']))
        future=plan(g,actors,0,width=8,rank_policy='future_copies')
        for candidate in (dp,baseline,future):
            result=replay(g,candidate,values)
            self.assertEqual(result['observed_native_outputs'],{n['output']:gold[n['output']] for n in g['operations']})
        # Detect a fabricated local hit and an omitted external commit.
        bad=deepcopy(dp);at=next(i for i,e in enumerate(bad['events']) if e['op']=='STORE');del bad['events'][at]
        with self.assertRaises(ValueError):replay(g,bad,values)
        bad=deepcopy(dp);at=next(i for i,e in enumerate(bad['events']) if e['op']=='LOAD_ZERO');del bad['events'][at]
        with self.assertRaises(ValueError):replay(g,bad,values)
        bad=deepcopy(dp);bad['copy_ticks']-=1
        with self.assertRaisesRegex(ValueError,'accounting'):replay(g,bad,values)

    def test_dp_can_spill_a_dirty_far_user_to_retain_a_frequently_reused_input(self):
        pairs=[('t','u')]
        for j in range(5):
            pairs.extend([('a','b'+str(j)),('n'+str(1+2*j),'c'+str(j))])
        pairs.append(('n0','a'));g=e_graph(pairs,{'n'+str(2+2*j) for j in range(5)}|{'n11'})
        actors={'E':{'kind':'E','words':3,'stride':1,'load_ticks':3,'store_ticks':5}}
        greedy=plan(g,actors,0,width=1);dp=plan(g,actors,0,width=32)
        self.assertLess(dp['copy_ticks'],greedy['copy_ticks'])
        for candidate in (greedy,dp):
            replay(g,candidate,{(o['tensor'],0):1 for o in g['objects'].values() if o['kind']=='external'})

    def test_capacity_unknown_addresses_missing_ack_and_unqualified_contract_rejected(self):
        g=e_graph([('a','b')],{'n0'})
        actor={'E':{'kind':'E','words':1,'stride':1,'load_ticks':1,'store_ticks':1}}
        self.assertEqual(plan(g,actor,0)['status'],'no_plan')
        bad=deepcopy(actor);bad['E']['stride']=8
        with self.assertRaises(ValueError):plan(g,bad,0)
        with self.assertRaises(ValueError):plan(g,actor,0,width=0)
        del g['objects']['a']['external_address']
        with self.assertRaisesRegex(ValueError,'addresses'):plan(g,actor,0)


if __name__=='__main__':unittest.main()
