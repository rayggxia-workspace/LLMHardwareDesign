from collections import Counter
import random
import unittest

from add_tile_recipe import aggregate_cost,commands,replay
from memory import descriptor_ticks
from s32_add_probe import components
from test_tile_recipe import fixture


class TestAddTileRecipe(unittest.TestCase):
    def fixture(self):
        h,q=fixture();q['kind']='native-s32-add-aggregate-v1'
        return q,h['virtual_memory'],h['leaf_inventory']['matrix']

    def test_literal_addressed_program_and_independent_integer_gold(self):
        rng=random.Random(220131);q,m,p=self.fixture()
        for _ in range(70):
            size=rng.randrange(1,32);n=rng.choice((2,3,5,17));tile=rng.randrange(1,9)
            signs=[rng.choice((-1,1)) for _ in range(n)]
            values=[[rng.randrange(-(1<<31),1<<31) for _ in range(n)] for _ in range(size)]
            # Include extreme/cancellation lanes without relying on random hit.
            values[0]=[2147483647 if i%2==0 else -2147483648 for i in range(n)]
            records={(i,j,k):v for i,row in enumerate(values) for j,x in enumerate(row) for k,v in enumerate(components(x))}
            result,counts,peak=replay(records,size,n,tile,signs=signs)
            self.assertEqual(result,[max(-(1<<31),min((1<<31)-1,sum(x*s for x,s in zip(row,signs)))) for row in values])
            expected=aggregate_cost(size,n,tile,q,m,p,signs=signs)
            for name,value in counts.items():self.assertEqual(expected[name],value,name)
            self.assertEqual(expected['P_words'],peak);self.assertFalse(expected['preparation_included'])
            # Independently add durations from the actual debug program. Do
            # not call the closed form to build this timing reference.
            ticks=0;rows=None
            for e in commands(size,n,tile,signs=signs):
                if e['op']=='LOAD':ticks+=descriptor_ticks(m,1,'load',p['io_write_ticks'])
                elif e['op']=='STORE':ticks+=descriptor_ticks(m,1,'store',p['io_read_ticks'])
                elif e['op']=='FEED':
                    rows=e['rows'];ticks+=q['feeder'][str(rows)]['reuse_b' if e['reuse_b'] else 'cold']
                else:ticks+=q['P'][str(rows)][{'SCALE':'scale','EXECUTE':'execute','READ_FINAL':'final_store'}[e['op']]]
            self.assertEqual(expected['ticks'],ticks)

    def test_capacity_unqualified_tail_and_corrupt_component_are_rejected(self):
        q,m,p=self.fixture()
        prepared={(i,j,k):v for i in range(8) for j in range(2) for k,v in enumerate(components(123456))}
        with self.assertRaises(ValueError):replay(prepared,8,2,8,capacity=512)
        bad=prepared.copy();bad[0,0,0]=32768
        with self.assertRaisesRegex(ValueError,'S16'):replay(bad,8,2,8)
        del q['P']['3']
        with self.assertRaisesRegex(ValueError,'qualified'):aggregate_cost(11,2,8,q,m,p)
        for args in ((0,2,1),(1,0,1),(1,2,9),(1,1<<63,1)):
            with self.assertRaises(ValueError):aggregate_cost(*args,q,m,p)

    def test_full_precision_decomposition_does_not_narrow_original_s32(self):
        for x in (-2147483648,-65537,-32769,-32768,-1,0,1,32767,32768,65535,65536,2147483647):
            lo,hi,flag=components(x)
            self.assertEqual(lo+(hi+flag)*65536,x)
            self.assertTrue(-32768<=lo<=32767 and -32768<=hi<=32767)


if __name__=='__main__':unittest.main()
