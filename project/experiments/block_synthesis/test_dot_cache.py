from copy import deepcopy
import random
import unittest
from unittest.mock import patch
import numpy as np

from dot_cache import variants
from dot_cache_replay import DotCache,order_program
from loop_dp import search,optimize
from streaming_ir import compile_graph
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost


def example(words=64,rows=2,k=5,columns=3,batch=()):
    h={'sites':{},'resources':{},'nets':{},'leaf_inventory':{},'virtual_memory':{
        'kind':'pr182-bounded-v1','channels':2,'period':6,'core_period':10,'slots':8,
        'queue':32,'bank_count':4,'bank_interleave_bytes':64,'row_bytes':1024,
        'bank_issue_cycles':2,'word_bytes':16,'credits':4,'phase':1,'latency':20,
        'row_miss_cycles':6,'turnaround_cycles':4,'address_bits':40}}
    # Synthetic unit measurements only. Formal 3B runs read native logs.
    for group,macro in [('matrix','M'),('vector','E')]:
        site=group+'.S';port=site+'.IO';h['sites'][site]={'words':words}
        h['resources'].update({group+'.'+macro:1,group+'.LC.service':1,port:1})
        h['leaf_inventory'][group]={'macros':[macro],'site':site,'io_resource':port,
            'io_read_ticks':3,'io_write_ticks':3,'memory_group':0}
        for d in ('read','write'):h['nets'][group+'.'+macro+'.'+d]={'cost':1,'fixed':False}
    outshape=[*batch,rows,columns]
    m={'values':{'a':{'shape':[*([1]*len(batch)),rows,k]},'b':{'shape':[*batch,k,columns]},'out':{'shape':outshape}},
       'tasks':[{'id':'mm','op':'MatMul','inputs':['a','b'],'outputs':['out']}]}
    program={'instructions':[{'id':'v','kernel':'mm','op':'Dot','inputs':['a','b'],
        'shape':outshape,'exponent':0,'bits':32,'attributes':{'length':k,'shift':0}}],
        'outputs':{'out':'v'},'initial_formats':{'a':{'bits':32},'b':{'bits':16}}}
    with patch('streaming_ir.duration',return_value=1):
        ir=compile_graph(m,h,[{'id':'mm','shape':outshape,'exponent':0}],{},program)
    return variants(ir)


class TestDotCache(unittest.TestCase):
    def test_cache_states_against_independent_exhaustive_choices(self):
        for seed in range(80):
            rng=random.Random(seed);h={'sites':{'S':{'words':32}},'resources':{'r':1},
                'nets':{'a':{'cost':1},'b':{'cost':1}},'incompatible_nets':[['a','b']]}
            tasks=[]
            for i in range(3):
                bs=[]
                for j in range(2):
                    tag=rng.choice('XY');ticks=rng.randint(3,10)
                    bs.append({'id':str(j),'site':'S','resources':['r'],'ticks':ticks,'warm_ticks':1,
                        'nets':[rng.choice('ab')],'scratch_words':12,'external_read_words':4,
                        'warm_read_words':1,'external_write_words':1,
                        'read_cache':{'site':'S','tag':tag,'stripe':1,'cache_words':3}})
                tasks.append({'id':str(i),'after':[str(i-1)] if i else [],'bindings':bs})
            feasible=[]
            from itertools import product
            for chosen in product(*(t['bindings'] for t in tasks)):
                nets=set().union(*(set(b['nets']) for b in chosen))
                if len(nets)>1:continue
                tag=None;time=traffic=0
                for b in chosen:
                    hit=tag==b['read_cache']['tag'];time+=1 if hit else b['ticks'];traffic+=2 if hit else 5
                    tag=b['read_cache']['tag']
                feasible.append((time,traffic,len(nets)))
            result=optimize(tasks,h,width=64)
            if not feasible:self.assertEqual(result['status'],'no_plan_in_bounded_search')
            else:
                self.assertEqual((result['makespan'],result['external_words'],result['wire_cost']),min(feasible))
                verify(tasks,h,result)

    def test_equal_time_states_keep_distinct_sram_contents(self):
        def b(tag,ticks=4):
            return {'id':tag,'site':'S','resources':['r'],'ticks':ticks,'warm_ticks':1,'nets':[],
                'scratch_words':12,'external_read_words':4,'warm_read_words':1,'external_write_words':1,
                'read_cache':{'site':'S','tag':tag,'stripe':1,'cache_words':3}}
        h={'sites':{'S':{'words':32}},'resources':{'r':1},'nets':{}}
        tasks=[{'id':'first','bindings':[b('A'),b('B')]},
               {'id':'next','after':['first'],'bindings':[b('B',10)]}]
        p=search(tasks,h,width=2)
        self.assertEqual(p['makespan'],5);self.assertEqual(p['tasks'][0]['binding'],'B')
        self.assertEqual(p['read_cache_hits'],1);verify(tasks,h,p)

    def test_resident_address_overlap_is_rejected_even_when_total_fits(self):
        ir=example();task=ir['tasks'][0]
        cached=max((b for b in task['bindings'] if 'read_cache' in b),key=lambda b:b['read_cache']['stripe'])
        task['bindings']=[cached]
        later={'id':'later','after':['mm'],'bindings':[{'id':'wide-scratch','site':'matrix.S',
            'resources':['matrix.S.IO'],'ticks':2,'scratch_words':12,'nets':[],
            'external_read_words':1,'external_write_words':0}]}
        tasks=[task,later];h=ir['hardware'];h['sites']['matrix.S']['words']=1024
        self.assertEqual(search(tasks,h)['status'],'no_plan_in_bounded_search')
        plain=deepcopy(tasks);plain[0]['bindings'][0].pop('read_cache')
        p=search(plain,h)
        p['tasks'][0]['cache_hit']=False
        with self.assertRaisesRegex(ValueError,'overlaps retained'):verify(tasks,h,p)

    def test_native_partial_reads_against_scalar_record_trace(self):
        # Enumerate real logical operand packets, not the planner formula.
        rng=random.Random(219)
        for _ in range(80):
            rows,columns,k=[rng.randint(1,7) for _ in range(3)]
            ca,cb=rng.choice((1,3)),rng.choice((1,3));t=rng.randint(0,k)
            for warm in (False,True):
                cache={('A',r,j,a) for r in range(rows) for j in range(t) for a in range(ca)} if warm else set()
                reads=0;zero=False
                for r in range(rows):
                    for col in range(columns):
                        for j in range(k):
                            staging=set()
                            for a in range(ca):
                                for b in range(cb):
                                    key=('A',r,j,a)
                                    if key not in cache:
                                        reads+=1
                                        if j<t:cache.add(key)
                                    if b not in staging:reads+=1;staging.add(b)
                                    if not zero:reads+=1;zero=True
                predicted=(0 if warm else rows*ca*t)+rows*columns*ca*cb*(k-t)+rows*columns*k*cb+1
                self.assertEqual(reads,predicted)

    def test_capacity_and_candidate_cost_independently_checked(self):
        for capacity in (8,9,15,64,2048):
            ir=example(capacity)
            with patch('verify_primitive_cost.duration',return_value=1):verify_cost(ir)
            p=optimize(ir['tasks'],ir['hardware'],width=8);verify(ir['tasks'],ir['hardware'],p)
            self.assertLessEqual(max(verify(ir['tasks'],ir['hardware'],p)['peak_words'].values()),capacity)
            if capacity==8:self.assertEqual(ir['read_cache_scope']['added_bindings'],0)

    def test_corrupt_cache_counts_addresses_and_capacity_fail(self):
        ir=example()
        for field,value in [('tag','wrong SSA'),('cache_words',0),('stripe',999),('cold_partial_external_reads',0)]:
            bad=deepcopy(ir);b=next(b for b in bad['tasks'][0]['bindings'] if b.get('read_cache',{}).get('stripe',0)>0)
            b['read_cache'][field]=value
            with patch('verify_primitive_cost.duration',return_value=1):
                with self.assertRaises(ValueError):verify_cost(bad)

    def test_repeated_ssa_retention_and_forged_hit(self):
        ir=example();task=deepcopy(ir['tasks'][0]);task['id']='second';task['after']=['mm']
        ir['tasks'].append(task)
        plan=optimize(ir['tasks'],ir['hardware'],width=32)
        self.assertEqual(plan['read_cache_hits'],1);verify(ir['tasks'],ir['hardware'],plan)
        bad=deepcopy(plan);bad['tasks'][0]['cache_hit']=True
        with self.assertRaisesRegex(ValueError,'cache hit'):verify(ir['tasks'],ir['hardware'],bad)

    def test_numeric_stripes_broadcast_tails_and_stale_data(self):
        rng=np.random.default_rng(219)
        for rows,k,columns in ((1,1,1),(2,7,3),(3,17,5)):
            ir=example(31,rows,k,columns);plan=optimize(ir['tasks'],ir['hardware'],width=8)
            cache=DotCache(ir,plan);node=ir['primitive_program']['instructions'][0]
            a=rng.integers(-(1<<30),1<<30,size=(rows,k),dtype=np.int64)
            b=rng.integers(-100,100,size=(k,columns),dtype=np.int64)
            self.assertTrue(np.array_equal(cache.dot(node,a,b),a@b));cache.report()
        ir=example();plan=optimize(ir['tasks'],ir['hardware'],width=8);cache=DotCache(ir,plan)
        node=ir['primitive_program']['instructions'][0];a=np.arange(10,dtype=np.int64).reshape(2,5);b=np.ones((5,3),dtype=np.int64)
        cache.dot(node,a,b);binding,row=cache.selected['mm'];row['cache_hit']=True
        self.assertTrue(np.array_equal(cache.dot(node,a,b),a@b))
        with self.assertRaisesRegex(ValueError,'immutable'):cache.dot(node,a+1,b)

    def test_batched_broadcast_and_noncontiguous_weight_view(self):
        ir=example(128,batch=(3,));plan=optimize(ir['tasks'],ir['hardware'],width=8)
        node=ir['primitive_program']['instructions'][0];cache=DotCache(ir,plan)
        a=np.arange(10,dtype=np.int64).reshape(1,2,5)-(1<<24)
        b=np.arange(45,dtype=np.int64).reshape(3,3,5).transpose(0,2,1)
        self.assertTrue(np.array_equal(cache.dot(node,a,b),a@b));cache.report()

    def test_ordering_resolves_views_but_never_executes_hidden_compute(self):
        p={'instructions':[
            {'id':'x','kernel':'A','op':'Product','inputs':['input']},
            {'id':'view','kernel':'metadata','op':'View','inputs':['x']},
            {'id':'y','kernel':'B','op':'Dot','inputs':['view']}], 'outputs':{'output':'y'}}
        self.assertEqual([n['id'] for n in order_program(p,{'tasks':[{'id':'A'},{'id':'B'}]})['instructions']],['x','view','y'])
        with self.assertRaisesRegex(ValueError,'dependency'):order_program(p,{'tasks':[{'id':'B'},{'id':'A'}]})


if __name__=='__main__':unittest.main()
