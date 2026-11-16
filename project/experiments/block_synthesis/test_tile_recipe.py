"""Closed form must match explicit command/descriptor execution, including tails."""
from collections import Counter
from copy import deepcopy
import random
import unittest

from memory import descriptor_ticks
from test_dot_cache import example
from tile_recipe import cost


def fixture():
    h = example()['hardware']
    q = {'kind':'native-p-e-tile-services-v1',
         'shapes':[[r,n] for r in range(1,9) for n in range(1,9)],
         'P':{str(r):{'scale':4,'execute':10*r+14,'final_store':12} for r in range(1,9)},
         'feeder':{str(r):{'cold':2*r+11,'reuse_b':2*r+7} for r in range(1,9)},
         'e_shift_store':21}
    return h,q


def enumerate_ticks(rows,columns,k,rt,ct,q,memory,p,e):
    # An intentionally literal event interpreter, not the planner's formula.
    counts = Counter();ticks = 0
    def event(kind,r=1):
        nonlocal ticks
        counts[kind]+=1
        if kind.endswith('load'):
            meta=e if kind=='e_load' else p
            ticks+=descriptor_ticks(memory,1,'load',meta['io_write_ticks'])
        elif kind.endswith('store') and kind!='final_store':
            meta=e if kind=='e_store' else p
            ticks+=descriptor_ticks(memory,1,'store',meta['io_read_ticks'])
        elif kind=='e_sign':ticks+=q['e_shift_store']
        elif kind in ('cold','reuse_b'):ticks+=q['feeder'][str(r)][kind]
        else:ticks+=q['P'][str(r)][kind]
    for _ in range(16):event('p_load')
    for rr in range(0,rows,rt):
        r=min(rt,rows-rr)
        for cc in range(0,columns,ct):
            n=min(ct,columns-cc)
            for _ in range(k):
                for _ in range(n):event('p_load')
                for component in range(3):
                    for _ in range(r):event('p_load')
                    event('reuse_b' if component else 'cold',r)
                    event('scale',r);event('execute',r)
            if n==1:
                for _ in range(r):event('final_store',r);event('p_store')
            else:
                for _ in range(r):
                    for _ in range(0,n,4):
                        event('final_store',r);event('p_store')
                        event('e_load');event('e_sign');event('e_store')
                    for _ in range(n):
                        for _ in range(3):
                            event('p_load');event('p_load');event('cold')
                            event('scale');event('execute')
                        event('final_store');event('p_store')
    return ticks,counts


class TestTileRecipe(unittest.TestCase):
    def test_random_tails_against_explicit_events(self):
        h,q=fixture();p=h['leaf_inventory']['matrix'];e=h['leaf_inventory']['vector'];m=h['virtual_memory']
        rng=random.Random(22061)
        for _ in range(120):
            rows,cols,k=[rng.randint(1,17) for _ in range(3)]
            rt,ct=rng.randint(1,8),rng.randint(1,8)
            expected,counts=enumerate_ticks(rows,cols,k,rt,ct,q,m,p,e)
            actual=cost(rows,cols,k,rt,ct,q,m,p,e)
            self.assertEqual(actual['ticks'],expected)
            self.assertEqual(actual['external_read_words'],counts['p_load']+counts['e_load'])
            self.assertEqual(actual.get('external_write_words',0),counts['p_store']+counts['e_store'])
            self.assertEqual(actual['canonical_outputs'],rows*cols)
            self.assertLessEqual(actual['temporary_external_words'],32)
            self.assertLessEqual(actual['P_words'],576)

    def test_column_reuse_is_A_not_unsupported_B_repacking(self):
        h,q=fixture();p=h['leaf_inventory']['matrix'];e=h['leaf_inventory']['vector'];m=h['virtual_memory']
        scalar=cost(2,8,2048,1,1,q,m,p)
        tile=cost(2,8,2048,2,8,q,m,p,e)
        self.assertEqual(scalar['dot_A_loads'],98304)
        self.assertEqual(tile['dot_A_loads'],12288)
        self.assertEqual(scalar['dot_B_loads'],32768)
        self.assertEqual(tile['dot_B_loads'],16384)
        self.assertEqual(tile['e_sign_services'],4)
        self.assertEqual(tile['scatter_basis_loads'],48)
        self.assertGreater(tile['external_read_words'],tile['dot_A_loads']+tile['dot_B_loads'])

    def test_missing_tail_and_E_or_overflow_rejected(self):
        h,q=fixture();p=h['leaf_inventory']['matrix'];e=h['leaf_inventory']['vector'];m=h['virtual_memory']
        q=deepcopy(q);q['shapes'].remove([2,3])
        with self.assertRaises(ValueError):cost(2,11,17,2,8,q,m,p,e)
        with self.assertRaises(ValueError):cost(2,8,17,2,8,q,m,p)
        with self.assertRaises(ValueError):cost(1,1,2**17,1,1,q,m,p)
        direct=cost(2,3,17,2,1,q,m,p)
        self.assertEqual(direct['E_words'],0)
        self.assertNotIn('e_sign_services',direct)

    def test_physical_or_control_overhead_is_not_hidden_in_native_profile(self):
        h,q=fixture();p=h['leaf_inventory']['matrix'];e=h['leaf_inventory']['vector'];m=h['virtual_memory']
        base=cost(2,8,7,2,8,q,m,p,e)
        slow=deepcopy(q);slow['e_shift_store']+=17
        changed=cost(2,8,7,2,8,slow,m,p,e)
        self.assertEqual(changed['ticks']-base['ticks'],17*base['e_sign_services'])
        self.assertEqual(changed['external_words'],base['external_words'])
