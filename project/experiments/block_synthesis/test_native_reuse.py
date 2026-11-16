from copy import deepcopy
from functools import lru_cache
from itertools import combinations
import random
import unittest

from native_reuse import rewrite,verify,Liveness
from resident_records import plan
from resident_replay import replay
from resident_timing import audit
from resident_bounds import FutureReuseCopies
from resident_records import State
from test_resident_records import e_graph


def graph(pairs,live):
    g=e_graph(pairs,live);g.update(kind='native-pointwise-ssa-v1',shape=[],index=0,
        primitives=[n['id'] for n in g['operations']])
    for n in g['operations']:n['primitive']=n['id']
    for o in g['objects'].values():o['abi']='eight native S16 lanes'
    return g


def actors(words=3,load=3,store=5):
    return {'E':{'kind':'E','words':words,'stride':1,'load_ticks':load,'store_ticks':store}}


def timing():
    return {'kind':'native-resident-services-v1','proof':{'synthetic':True},'rtl_sha256':{'fixture':'unit'},
        'profile':{'P':{'0':4},'E':{'37':20},'feeder':{'0':13}}}


def exact_e_suffix(g,capacity,load,store):
    """Independent set-based enumeration: no allocator or liveness calls."""
    ops=g['operations'];produced={n['output'] for n in ops};live=set(g['live_out'].values())
    def subsets(items):
        items=sorted(items)
        for count in range(len(items)+1):
            for row in combinations(items,count):yield frozenset(row)
    @lru_cache(None)
    def solve(i,cache,backed):
        if i==len(ops):
            cost=0;arrived=set(cache)
            for c in g['external_commits']:
                v=c['record']
                if c['external_address']==g['objects'][v]['external_address'] and v in backed:continue
                if v not in arrived:
                    if v not in backed:return float('inf')
                    cost+=load;arrived.add(v)
                cost+=store
            return cost
        n=ops[i];out=n['output'];needed=set(n['inputs'])
        future=live|{x for later in ops[i+1:] for x in later['inputs']}|{
            later['output'] for later in ops[i+1:] if later.get('reuse_of')}
        best=float('inf')
        if n.get('reuse_of') and out in cache|backed:
            best=solve(i+1,frozenset(cache&future),frozenset(backed&future))
        def charge(victims,b):
            dirty=(victims&future&produced)-b;optional=set()
            for v in dirty:
                if v in needed:continue
                next_read=next((j for j in range(i+1,len(ops)) if v in ops[j]['inputs']),len(ops))
                next_write=next((j for j in range(i,len(ops)) if ops[j].get('reuse_of')==v),len(ops)+1)
                if next_write<=next_read:optional.add(v)
            for dropped in subsets(optional):yield b|dirty-dropped,len(dirty-dropped)*store
        if any(v in produced and v not in cache|backed for v in needed):return best
        for before in subsets(cache|needed):
            if not needed<=before or len(before)>capacity:continue
            for b1,c1 in charge(cache-before,backed):
                base=len(before-cache)*load+c1+20
                for after in subsets(before|{out}):
                    if out not in after or len(after)>capacity:continue
                    for b2,c2 in charge(before-after,b1):
                        best=min(best,base+c2+solve(i+1,frozenset(after&future),frozenset(b2&future)))
        return best
    return solve


class TestNativeReuse(unittest.TestCase):
    def test_m_identity_preserves_scale_width_shift_terms_and_real_b_bank(self):
        from test_resident_timing import graph as matrix_graph,timing as matrix_timing
        g=matrix_graph();g.update(kind='native-pointwise-ssa-v1',shape=[],index=0,primitives=['n0','n1','n2'])
        for o in g['objects'].values():o['abi']='canonical low S32 record'
        for n in g['operations']:n['primitive']=n['id']
        r=rewrite(g);self.assertEqual(r['operations'][2]['reuse_of'],'n0')
        for field,value in (('width',16),('shift',1),('k',2)):
            changed=deepcopy(g);changed['operations'][2][field]=value
            self.assertNotIn('reuse_of',rewrite(changed)['operations'][2])
        for field,value in (('coefficient',-1),('scale_shift',16)):
            changed=deepcopy(g);changed['operations'][2]['terms'][0][field]=value
            self.assertNotIn('reuse_of',rewrite(changed)['operations'][2])
        a={'M':{'kind':'M','words':16,'stride':8,'load_ticks':1,'store_ticks':1}}
        p=plan(r,a,0,width=8,rank_policy='future_copies',service_timing=matrix_timing())
        values={('a',0):7,('b',0):-9,('c',0):13}
        result=replay(r,p,values);audit(p,matrix_timing())
        self.assertEqual(result['logical_native_outputs'],{'n0':(-63)&0xffffffff,'n1':91,'n2':(-63)&0xffffffff})
        self.assertEqual(p['reused_operations'],1)

    def test_exact_set_oracle_and_lower_bound_with_optional_recomputation(self):
        rng=random.Random(220181);checked=0
        for _ in range(12):
            pairs=[('a','b'),rng.choice((('a','c'),('n0','c'))),('a','b'),('n1','n2')]
            g=rewrite(graph(pairs,{'n3',rng.choice(('n0','n2'))}));a=actors(rng.choice((2,3)),3,5)
            capacity=a['E']['words'];solve=exact_e_suffix(g,capacity,3,5)
            p=plan(g,a,0,width=None,service_timing=timing(),rank_policy='future_copies')
            self.assertEqual(p['total_ticks'],solve(0,frozenset(),frozenset()))
            bound=FutureReuseCopies(g,a,service_timing=timing())
            for i in range(5):
                defined={n['output'] for n in g['operations'][:i]}
                pool=sorted({'a','b','c'}|defined)
                for _ in range(15):
                    cache=frozenset(rng.sample(pool,rng.randrange(min(capacity,len(pool))+1)))
                    backed=frozenset(x for x in defined if rng.randrange(2))
                    exact=solve(i,cache,backed)
                    state=State((tuple(sorted(cache))+(None,)*(capacity-len(cache)),),backed,(frozenset(),),(None,))
                    self.assertLessEqual(bound.bound(state,i),exact,(i,cache,backed));checked+=1
        self.assertEqual(checked,900)

    def run_plan(self,g,*,words=3,load=3,store=5,width=8,rank='future_copies',values=None):
        r=rewrite(g);p=plan(r,actors(words,load,store),0,width=width,rank_policy=rank,service_timing=timing())
        values=values or {(o['tensor'],0):(-7 if o['tensor']=='a' else 13) for o in g['objects'].values() if o['kind']=='external'}
        observed=replay(r,p,values);audit(p,timing())
        old=plan(g,actors(words,load,store),0,width=width,service_timing=timing())
        gold=replay(g,old,values)['observed_native_outputs']
        self.assertEqual(observed['logical_native_outputs'],{n['id']:gold[n['output']] for n in g['operations']})
        return r,p,observed,values

    def test_reuse_keeps_distinct_original_output_commits(self):
        g=graph([('a','b'),('a','b')],{'n0','n1'})
        r,p,obs,values=self.run_plan(g)
        self.assertEqual(p['reused_operations'],1);self.assertEqual(p['external_store_words'],2)
        self.assertEqual(len(r['external_commits']),2)
        self.assertEqual(sum(e['op']=='E' for e in p['events']),1)
        bad=deepcopy(p);bad['events']=[e for e in bad['events'] if e['op']!='STORE_COMMIT']
        with self.assertRaisesRegex(ValueError,'committed'):replay(r,bad,values)

    def test_canonical_temporary_is_not_an_extra_required_output(self):
        g=graph([('a','b'),('a','b')],{'n1'})
        r,p,_,values=self.run_plan(g)
        self.assertEqual(p['external_store_words'],1)
        self.assertEqual([e['external_address'] for e in p['events'] if e['op']=='STORE_COMMIT'],
                         [g['objects']['n1']['external_address']])
        bad=deepcopy(r);bad['external_commits'][0]['external_address']+=1
        with self.assertRaisesRegex(ValueError,'commit'):verify(bad,g)

    def test_recompute_and_dirty_discard_are_real_frontier_choices(self):
        g=graph([('a','b'),('a','c'),('a','b')],{'n2'})
        r,p,_,values=self.run_plan(g,words=2,load=1,store=100)
        self.assertTrue(any(e['op']=='DISCARD' for e in p['events']))
        self.assertEqual(p['recomputed_duplicate_operations'],1)
        self.assertEqual(p['reused_operations'],0)
        self.assertEqual(p['external_store_words'],1)
        self.assertTrue(Liveness(r).may_discard(1,'n0'))
        self.assertFalse(Liveness(r).may_discard(0,'a'))
        bad=deepcopy(p);e=next(e for e in bad['events'] if e['op']=='DISCARD');e['record']='a'
        with self.assertRaises(ValueError):replay(r,bad,values)

    def test_external_backed_reuse_still_pays_actual_reload(self):
        g=graph([('a','b'),('n0','c'),('d','e'),('a','b')],{'n0','n1','n2','n3'})
        r,p,_,_=self.run_plan(g,words=2,load=1,store=1)
        self.assertGreater(p['reused_operations'],0)
        self.assertTrue(any(e['op']=='LOAD' and e['record']=='n0' for e in p['events']))

    def test_last_recompute_point_is_consumed_before_tail_output_reloads(self):
        # The first alias output needs a reload while the last recomputed
        # output still has its only dirty S copy. The last definition is no
        # longer a future write during these tail commits.
        g=graph([('a','b'),('c','d'),('e','f'),('n1','n2'),('c','d'),('n1','n2')],['n4','n2','n5'])
        for width in (1,8,None):
            r,p,_,_=self.run_plan(g,words=2,width=width,load=1,store=100)
            tail=next(i for i,e in enumerate(p['events']) if e['op'] in ('E','M_FINAL','REUSE') and e['native']=='n5')
            self.assertFalse(any(e['op']=='DISCARD' for e in p['events'][tail+1:]))

    def test_element_relocation_keeps_canonical_scratch_and_each_output_array(self):
        from resident_loop_replay import element
        g=graph([('a','b'),('a','b')],{'n1'});g['shape']=[3]
        for i,o in enumerate(g['objects'].values()):o['external_address']=100+10*i
        r,p,_,_=self.run_plan(g)
        recipe={'graph':r,'plan':p,'loop':{'elements':3,'sources':{'a':'element','b':'element'}}}
        for i in range(3):
            relocated,body=element(recipe,i)
            self.assertEqual(relocated['objects']['n0']['external_address'],g['objects']['n0']['external_address']+i)
            self.assertEqual(relocated['external_commits'][0]['external_address'],g['objects']['n1']['external_address']+i)
            replay(relocated,body,{('a',i):-i,('b',i):12})

    def test_bit_contract_changes_and_forged_proofs_are_rejected(self):
        g=graph([('a','b'),('a','b')],{'n1'});r=rewrite(g)
        for mutate in (lambda x:x['operations'][1].update(shift=1),
                       lambda x:x['operations'][1].update(opcode=6),
                       lambda x:x['operations'][1].update(inputs=['b','a']),
                       lambda x:x['objects']['n1'].update(abi='different'),
                       lambda x:x['operations'].reverse()):
            bad=deepcopy(r);mutate(bad)
            with self.assertRaises(ValueError):verify(bad,g)
        changed=deepcopy(g);changed['operations'][1]['shift']=1
        self.assertNotIn('reuse_of',rewrite(changed)['operations'][1])
        changed=deepcopy(g);changed['objects']['n1']['abi']='different'
        self.assertNotIn('reuse_of',rewrite(changed)['operations'][1])
        bad=deepcopy(r);bad['objects']['a']['external_address']+=1
        with self.assertRaisesRegex(ValueError,'address/index'):verify(bad,g)

    def test_no_fabricated_reuse_or_work_counters(self):
        g=graph([('a','b'),('a','b')],{'n1'});r,p,_,values=self.run_plan(g)
        bad=deepcopy(p);e=next(e for e in bad['events'] if e['op']=='REUSE');e['address']=999
        with self.assertRaises(ValueError):replay(r,bad,values)
        bad=deepcopy(p);bad['reused_operations']+=1
        with self.assertRaisesRegex(ValueError,'accounting'):replay(r,bad,values)
        bad=deepcopy(p);e=next(e for e in bad['events'] if e['op']=='REUSE')
        e.update(where='external',external_address=r['objects'][e['record']]['external_address'])
        with self.assertRaisesRegex(ValueError,'backing'):replay(r,bad,values)

    def test_exhaustive_and_bounded_policies_share_real_actions(self):
        for pairs in ([('a','b'),('a','c'),('a','b')],
                      [('a','b'),('a','b'),('n0','n1')]):
            g=graph(pairs,{'n2'})
            plans=[]
            for width in (1,8,None):
                for rank in ('copy_cost','future_copies'):
                    _,p,_,_=self.run_plan(g,words=2,width=width,rank=rank);plans.append(p)
            exact=[p['total_ticks'] for p in plans if p['width'] is None]
            self.assertEqual(exact[0],exact[1])
            self.assertLessEqual(exact[0],min(p['total_ticks'] for p in plans))


if __name__=='__main__':unittest.main()
