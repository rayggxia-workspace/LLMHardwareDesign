import random
import unittest
from copy import deepcopy
from unittest.mock import patch
import numpy as np
from preparation_reuse import recipe, address, unpack, lower
from test_dot_cache import example
from dot_cache import variants
from dot_cache_replay import DotCache
from loop_dp import optimize
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost


class TestPreparationReuse(unittest.TestCase):
    def plain(self,**kwargs):
        ir=example(**kwargs)
        for task in ir['tasks']:
            task['bindings']=[b for b in task['bindings'] if 'read_cache' not in b]
        ir.pop('read_cache_scope',None)
        return ir

    def test_lowered_work_and_selected_sram_replay(self):
        rng=np.random.default_rng(219)
        for batch in [(),(2,)]:
            ir=self.plain(rows=2,k=5,columns=3,batch=batch)
            before=deepcopy(ir);lower(ir);variants(ir,state_cost=True)
            with patch('verify_primitive_cost.duration',return_value=1):verify_cost(ir)
            plan=optimize(ir['tasks'],ir['hardware']);verify(ir['tasks'],ir['hardware'],plan)
            old=optimize(before['tasks'],before['hardware'])
            self.assertLess(plan['makespan'],old['makespan'])
            self.assertEqual(plan['nets'],old['nets'])
            a=rng.integers(-(1<<31),1<<31,size=(*([1]*len(batch)),2,5),dtype=np.int64)
            b=rng.integers(-32768,32768,size=(*batch,5,3),dtype=np.int64)
            cache=DotCache(ir,plan);node=ir['primitive_program']['instructions'][0]
            np.testing.assert_array_equal(cache.dot(node,a,b),np.matmul(a,b))
            report=cache.report();self.assertEqual(report['preparation']['calls'],1)
            p=ir['operand_preparations']['v']
            self.assertEqual(report['preparation']['events'][0]['split_calls'],p['rows']*5)

    def test_independent_checker_rejects_forged_preparation(self):
        ir=lower(self.plain())
        with patch('verify_primitive_cost.duration',return_value=1):
            verify_cost(ir)
            for field,value in [('input','wrong'),('rows',19),('external_words',1),('external_base',0),('new_split_calls',0)]:
                bad=deepcopy(ir);bad['operand_preparations']['v'][field]=value
                with self.assertRaises(ValueError):verify_cost(bad)
            bad=deepcopy(ir);bad['program'][0]['body']['sequence'][0]['sequence'][0]['repeat']=0
            with self.assertRaises(ValueError):verify_cost(bad)

    def test_capacity_falls_back_without_allocating_or_changing_work(self):
        ir=self.plain();original=deepcopy(ir)
        ir['hardware']['external_capacity_words']=ir['required_external_bytes']//16
        lower(ir)
        self.assertEqual(ir['operand_preparations'],{})
        self.assertEqual(ir['tasks'],original['tasks'])
        self.assertEqual(ir['required_external_bytes'],original['required_external_bytes'])
        with self.assertRaisesRegex(ValueError,'before cache'):lower(example())

    def test_addresses_and_native_component_identity(self):
        rng=random.Random(219)
        for rows,k,columns in [(1,1,2),(2,5,3),(3,7,9)]:
            node={'id':'dot','op':'Dot','inputs':['a','b'],'shape':[rows,columns],'attributes':{'length':k}}
            p=recipe(node,[3,1],11,11+3*rows*k)
            memory={}; source={}; writes=[]
            for r in range(rows):
                for j in range(k):
                    raw=rng.randrange(-(1<<31),1<<31);source[r,j]=raw
                    for c,value in enumerate(unpack(raw)):
                        addr=address(p,r,j,c); writes.append(addr); memory[addr]=value
            self.assertEqual(len(set(writes)),3*rows*k)
            self.assertEqual(set(writes),set(range(11,11+3*rows*k)))
            # Output-column iterations read the same prepared records, without
            # rewriting them; no packing or extra arithmetic is free here.
            for r in range(rows):
                for n in range(columns):
                    for j in range(k):
                        lo,hi,neg=[memory[address(p,r,j,c)] for c in range(3)]
                        self.assertEqual(lo+65536*(hi+neg),source[r,j])
            self.assertEqual(p['old_split_calls']-p['new_split_calls'], rows*k*(columns-1))

    def test_capacity_and_inapplicable_shapes(self):
        n={'id':'x','op':'Dot','inputs':['a','b'],'shape':[2,3],'attributes':{'length':5}}
        self.assertIsNone(recipe(n,[3,1],10,39))
        self.assertIsNotNone(recipe(n,[3,1],10,40))
        self.assertIsNone(recipe(n,[1,1],0,100))
        p=recipe(n,[3,1],10,40)
        for index in [(-1,0,0),(2,0,0),(0,5,0),(0,0,3)]:
            with self.assertRaises(ValueError):address(p,*index)


if __name__=='__main__':unittest.main()
