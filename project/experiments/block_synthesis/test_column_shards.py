from copy import deepcopy
from types import SimpleNamespace
import unittest
import random
from unittest.mock import patch

import numpy as np

from column_shards import variants_for,expand_selected
from dot_cache import variants
from dot_cache_replay import DotCache
from loop_dp import optimize,search
from preparation_reuse import lower as prepare
from primitive_stages import lower
from search_diagnostics import bounds
from test_dot_cache import example
from transition import evaluate_transition
from verify_loop_dp import verify,_resize_columns
from verify_primitive_cost import verify as verify_cost


def fixture(*,shared=False,columns=9,k=5,words=64,batch=(),matrices=2):
    ir=example(columns=columns,k=k,words=words,batch=batch)
    for t in ir['tasks']:t['bindings']=[b for b in t['bindings'] if 'read_cache' not in b]
    ir.pop('read_cache_scope')
    h=ir['hardware']
    for i in range(1,matrices):
        target='second_matrix' if i==1 else 'matrix_'+str(i)
        meta=deepcopy(h['leaf_inventory']['matrix']);meta.update(site=target+'.S',
            io_resource=target+'.S.IO',memory_group=0 if shared else i)
        h['leaf_inventory'][target]=meta;h['sites'][meta['site']]=deepcopy(h['sites']['matrix.S'])
        for field in ('io_resource','memory_group'):
            if field in h['sites'][meta['site']]:h['sites'][meta['site']][field]=meta[field]
        for field in ('resources','nets'):
            for name,value in list(h[field].items()):
                if name.startswith('matrix.'):h[field][target+name[len('matrix'):]]=deepcopy(value)
    return variants_for(variants(lower(prepare(ir)),state_cost=True))


def compound(ir):
    task=next(t for t in ir['tasks'] if t['id']=='v')
    return next(b for b in task['bindings'] if 'parallel_shards' in b and
                all(c['binding'].get('read_cache',{}).get('stripe')==5
                    for c in b['parallel_shards']['children']))


def initial(ir):
    return SimpleNamespace(resources={r:(0,)*n for r,n in ir['hardware']['resources'].items()},
        nets=frozenset(),cache={},makespan=0)


class TestColumnShards(unittest.TestCase):
    def audit(self,ir):
        with patch('verify_primitive_cost.duration',return_value=1):return verify_cost(ir)

    def test_native_proof_schedule_numeric_and_same_pool_search(self):
        ir=fixture();self.audit(ir);b=compound(ir)
        next(t for t in ir['tasks'] if t['id']=='v')['bindings']=[b]
        plan=optimize(ir['tasks'],ir['hardware'],width=8)
        verify(ir['tasks'],ir['hardware'],plan)
        expanded,flat=expand_selected(ir['tasks'],plan)
        self.assertEqual(len(expanded),len(ir['tasks'])+1)
        verify(expanded,ir['hardware'],flat)
        self.assertLessEqual(bounds(ir['tasks'],ir['hardware'],plan)['completion_lower_bound'],plan['makespan'])
        rng=np.random.default_rng(219)
        a=rng.integers(-(1<<31),1<<31,size=(2,5),dtype=np.int64)
        weights=rng.integers(-32768,32768,size=(5,9),dtype=np.int64)
        cache=DotCache(ir,plan);node=ir['primitive_program']['instructions'][0]
        np.testing.assert_array_equal(cache.dot(node,a,weights),a@weights)
        report=cache.report();self.assertEqual(report['calls'],2)
        self.assertEqual(report['preparation']['calls'],1)

    def test_actual_channel_contention_and_frontier_availability(self):
        parallel=fixture();serial=fixture(shared=True)
        b=compound(parallel);policies=('preserve',)*2
        free=evaluate_transition(initial(parallel),b,parallel['hardware'],0,retention=policies)
        occupied=initial(parallel);occupied.resources['second_matrix.M']=(10**6,)
        delayed=evaluate_transition(occupied,b,parallel['hardware'],0,retention=policies)
        self.assertGreater(delayed['end'],free['end'])
        seq=evaluate_transition(initial(serial),compound(serial),serial['hardware'],0,retention=policies)
        intervals=seq['details']['services']
        self.assertEqual(intervals[1]['start'],intervals[0]['end'])
        self.assertGreater(seq['duration'],free['duration'])
        self.assertEqual(seq['traffic'],free['traffic'])

    def test_partial_hits_recomputed_per_child(self):
        ir=fixture();b=compound(ir);state=initial(ir);c=b['parallel_shards']['children'][0]['binding']['read_cache']
        cold=evaluate_transition(state,b,ir['hardware'],0,retention=('preserve','preserve'))
        state.cache[c['site']]=(c['tag'],2,2*c['rows']*c['components'][0])
        hot=evaluate_transition(state,b,ir['hardware'],0,retention=('preserve','preserve'))
        self.assertEqual(cold['traffic']-hot['traffic'],2*c['rows']*c['components'][0])
        self.assertEqual(hot['details']['services'][0]['evaluation']['reused_prefix'],2)
        self.assertEqual(hot['details']['services'][1]['evaluation']['reused_prefix'],0)

    def test_frontier_partition_matches_all_integer_splits(self):
        ir=fixture(columns=9);self.audit(ir)
        b=next(b for t in ir['tasks'] for b in t['bindings'] if 'frontier_partition' in b and
               all(c['binding']['read_cache']['stripe']==5 for c in b['parallel_shards']['children']))
        for seed in range(50):
            rng=random.Random(seed);state=initial(ir)
            for child in b['parallel_shards']['children']:
                c=child['binding']['read_cache'];group=child['binding']['macro_binding']['M']
                state.resources[group+'.M']=(rng.randint(0,20000),)
                prefix=rng.randint(0,5)
                if prefix:state.cache[c['site']]=(c['tag'],prefix,prefix*c['rows']*c['components'][0])
            actual=evaluate_transition(state,b,ir['hardware'],0,retention=('preserve','preserve'))
            best=None
            for width in range(1,9):
                ends=[]
                for original,interval in zip(b['parallel_shards']['children'],([0,width],[width,9])):
                    child=_resize_columns(original,interval)['binding'];c=child['read_cache'];old=state.cache.get(c['site'])
                    reuse=min(old[1],c['stripe']) if old and old[0]==c['tag'] else 0
                    duration=child['ticks']-reuse*c['rows']*c['components'][0]*c['load_ticks']
                    ends.append(max(state.resources[r][0] for r in child['resources'])+duration)
                candidate=max(ends);best=candidate if best is None else min(best,candidate)
            self.assertEqual(actual['end'],best)
        next(t for t in ir['tasks'] if t['id']=='v')['bindings']=[b]
        plan=optimize(ir['tasks'],ir['hardware']);verify(ir['tasks'],ir['hardware'],plan)
        rng=np.random.default_rng(220);a=rng.integers(-100000,100000,size=(2,5),dtype=np.int64)
        weights=rng.integers(-10000,10000,size=(5,9),dtype=np.int64)
        cache=DotCache(ir,plan)
        np.testing.assert_array_equal(cache.dot(ir['primitive_program']['instructions'][0],a,weights),a@weights)
        self.assertEqual(cache.report()['calls'],2)
        bad=deepcopy(plan);bad['tasks'][-1]['evaluation']['resolved_columns'][0][1]+=1
        with self.assertRaisesRegex(ValueError,'gap/overlap'):verify(ir['tasks'],ir['hardware'],bad)

    def test_independent_checkers_reject_ranges_counts_and_schedule(self):
        ir=fixture();self.audit(ir)
        for field in ('gap','cost','resource','scratch','nets','cache-model'):
            bad=deepcopy(ir);b=compound(bad);child=b['parallel_shards']['children'][0]
            if field=='gap':child['columns'][1]-=1
            elif field=='cost':child['binding']['ticks']-=1
            elif field=='resource':child['binding']['resources'].pop()
            elif field=='scratch':child['binding']['scratch_by_site'][child['binding']['site']]+=1
            elif field=='nets':child['binding']['nets'].pop()
            else:child['binding']['read_cache']['cost_model']='unknown'
            with self.assertRaises(ValueError):self.audit(bad)
        next(t for t in ir['tasks'] if t['id']=='v')['bindings']=[compound(ir)]
        plan=optimize(ir['tasks'],ir['hardware'])
        bad=deepcopy(plan);bad['tasks'][-1]['evaluation']['services'][0]['end']-=1
        with self.assertRaises(ValueError):verify(ir['tasks'],ir['hardware'],bad)
        bad=deepcopy(plan);bad['tasks'][-1]['end']-=1
        with self.assertRaisesRegex(ValueError,'compound time'):verify(ir['tasks'],ir['hardware'],bad)

    def test_partition_search_is_bounded_and_not_hardware_count_specific(self):
        ir=fixture(columns=11)
        self.assertGreater(ir['column_shard_scope']['added_bindings'],0)
        self.assertEqual(ir['column_shard_scope']['truncated_families'],0)
        self.audit(ir)
        with self.assertRaisesRegex(ValueError,'already'):variants_for(ir)

    def test_three_M_two_channels_broadcast_and_long_K_numeric(self):
        for matrices,batch,k in ((3,(),257),(2,(2,),257)):
            ir=fixture(columns=11,matrices=matrices,batch=batch,k=k);self.audit(ir)
            task=next(t for t in ir['tasks'] if t['id']=='v')
            b=next(b for b in task['bindings'] if 'parallel_shards' in b and
                   len(b['parallel_shards']['children'])==matrices and
                   all(c['binding'].get('read_cache',{}).get('stripe',0)>0
                       for c in b['parallel_shards']['children']))
            task['bindings']=[b];plan=optimize(ir['tasks'],ir['hardware'])
            verify(ir['tasks'],ir['hardware'],plan)
            rng=np.random.default_rng(219+matrices)
            a=rng.integers(-(1<<31),1<<31,size=(*([1]*len(batch)),2,k),dtype=np.int64)
            weights=rng.integers(-32768,32768,size=(*batch,k,11),dtype=np.int64)
            cache=DotCache(ir,plan)
            np.testing.assert_array_equal(cache.dot(ir['primitive_program']['instructions'][0],a,weights),a@weights)
            self.assertEqual(cache.report()['calls'],matrices)

    def test_compound_dp_against_independent_complete_small_schedules(self):
        # A separate append-calendar enumerator: never calls the transition
        # evaluator. Includes unequal resource times and fork/join orderings.
        for seed in range(40):
            rng=random.Random(seed)
            h={'resources':{'m0':1,'m1':1,'bus':1},
               'sites':{'s0':{'words':32},'s1':{'words':32}},
               'nets':{'n0':{'cost':1},'n1':{'cost':1}}}
            def leaf(name,site,ticks,shared=False):
                index=site[-1]
                return {'id':name,'site':site,'ticks':ticks,'resources':['m'+index]+(['bus'] if shared else []),
                        'nets':['n'+index],'scratch_words':8,'scratch_by_site':{site:8},
                        'external_read_words':ticks,'external_write_words':1}
            tasks=[]
            for i in range(3):
                ident=str(i);a=leaf('a','s0',rng.randint(3,12));b=leaf('b','s1',rng.randint(3,12))
                left=leaf('left','s0',rng.randint(1,6),seed%2==0)
                right=leaf('right','s1',rng.randint(1,6),seed%2==0)
                pair={'id':'pair','site':'s0','ticks':max(left['ticks'],right['ticks']),
                      'resources':sorted(set(left['resources']+right['resources'])),'nets':['n0','n1'],
                      'scratch_words':8,'scratch_by_site':{'s0':8,'s1':8},
                      'external_read_words':left['ticks']+right['ticks'],'external_write_words':2,
                      'parallel_shards':{'kind':'dot-columns-v1','primitive':ident,'columns':2,
                           'children':[{'columns':[0,1],'binding':left},{'columns':[1,2],'binding':right}]}}
                tasks.append({'id':ident,'after':(['0','1'] if i==2 else []),'bindings':[a,b,pair]})
            best=[None]
            def visit(done,calendar,nets,traffic):
                if len(done)==3:
                    result=(max(done.values()),traffic,len(nets))
                    if best[0] is None or result<best[0]:best[0]=result
                    return
                for t in tasks:
                    if t['id'] in done or any(p not in done for p in t['after']):continue
                    ready=max((done[p] for p in t['after']),default=0)
                    for b in t['bindings']:
                        parts=[c['binding'] for c in b['parallel_shards']['children']] if 'parallel_shards' in b else [b]
                        times=calendar.copy();finish=[];demand=nets.copy();words=traffic
                        for p in parts:
                            end=max([ready]+[times[r] for r in p['resources']])+p['ticks']
                            finish.append(end)
                            for r in p['resources']:times[r]=end
                            demand.update(p['nets']);words+=p['external_read_words']+p['external_write_words']
                        visit({**done,t['id']:max(finish)},times,demand,words)
            visit({},dict.fromkeys(h['resources'],0),set(),0)
            plan=search(tasks,h,width=10000,ready_limit=3)
            self.assertEqual((plan['makespan'],plan['external_words'],plan['wire_cost']),best[0])
            verify(tasks,h,plan)


if __name__=='__main__':unittest.main()
