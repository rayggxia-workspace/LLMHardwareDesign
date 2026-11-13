from copy import deepcopy
import random
import unittest
from native_lane_cover import candidates,cover,verify
from native_pointwise import execute
from resident_batch import plan
from resident_batch_graph import build,verify as verify_tile
from test_resident_batch import case
from test_resident_operand_mask import contract
from verify_resident_batch import replay


class TestNativeLaneCover(unittest.TestCase):
    def test_unrelated_term_must_keep_K1_with_nonzero_second_lane(self):
        # Synthetic native contract, checked against the original word-level
        # interpreter. Unlike the model's constant-one terms, this extra B
        # has a nonzero high lane, so widening every term would be wrong.
        _,base,actors,q,scalar=case();graphs=deepcopy(base['graphs'])
        for g in graphs:
            high=next(n for n in g['operations'] if n['kind']=='M' and n['k']==2 and len(n['terms'])==1
                      and g['objects'][n['terms'][0]['b']].get('literal')==65536
                      and g['objects'][n['terms'][0]['a']]['kind']=='external')
            consumer=next(n for n in g['operations'] if n['kind']=='M' and n['k']==1
                          and any(t['a']==high['output'] and g['objects'][t['b']].get('literal')==1 for t in n['terms']))
            y=next(v for v,o in g['objects'].items() if o['kind']=='external' and o.get('tensor')=='y')
            consumer['terms'].append({'a':high['terms'][0]['a'],'b':y,'coefficient':1,'scale_shift':0})
            consumer['inputs']=list(dict.fromkeys(v for t in consumer['terms'] for v in (t['a'],t['b'])))
        source=build(graphs,scratch_start=1250,external_capacity_words=3000,max_rows=3)
        folded=cover(source);program=plan(folded,actors,1000,q,scalar,width=2,operand_contract=contract(q))
        values={('x',i):(i+1)*65536+17 for i in range(3)}|{('y',i):(i+2)*65536+19 for i in range(3)}|{('one',0):1}
        observed=replay(folded,program,values)['observed_native_outputs']
        for rr,g in enumerate(graphs):
            gold=execute(g,values)
            for primitive,key in g['primitive_outputs'].items():self.assertEqual(observed[folded['graph']['primitive_outputs'][f'{rr}:{primitive}']],gold[key])
        with self.assertRaises(ValueError):
            wrong=deepcopy(folded)
            for n in wrong['graph']['operations']:
                if n['kind']=='M' and any(t.get('k')==2 for t in n['terms']):
                    for t in n['terms']:t['k']=2
            verify(wrong)

    def test_dynamic_cover_preserves_S32_and_static_sources_are_excluded(self):
        _,tile,actors,q,scalar=case();options=candidates(tile)
        self.assertTrue(options)
        self.assertTrue(all('literal' not in tile['graph']['objects'][r['raw']] for r in options.values()))
        folded=cover(tile);self.assertEqual(verify_tile(folded)['covered_dynamic_extractions'],len(options))
        self.assertLess(len(folded['graph']['operations']),len(tile['graph']['operations']))
        variants=[plan(folded,actors,1000,q,scalar,width=w,schedule=s,operand_contract=contract(q))
                  for w,s in ((1,'fixed'),(2,'fixed'),(1,'ready'))]
        rng=random.Random(21924)
        for edge in (-2147483648,-65537,-32769,-32768,-1,0,32768,65535,65536,2147483647):
            values={('x',i):edge for i in range(3)}|{('y',i):rng.randrange(-(1<<31),1<<31) for i in range(3)}|{('one',0):1}
            for program in variants:
                got=replay(folded,program,values)['observed_native_outputs']
                for rr,g in enumerate(tile['graphs']):
                    gold=execute(g,values)
                    for primitive,key in g['primitive_outputs'].items():
                        self.assertEqual(got[folded['graph']['primitive_outputs'][f'{rr}:{primitive}']],gold[key])
        self.assertTrue(any(e['k']==2 for p in variants for e in p['events'] if e['op']=='ROW_M_TERM'))

    def test_cover_rejects_changed_source_terms_outputs_and_wrong_K(self):
        _,tile,actors,q,scalar=case();good=cover(tile)
        for fault in ('basis','K','coefficient','output','order','source','static'):
            bad=deepcopy(good)
            n=next(n for n in bad['graph']['operations'] if n['kind']=='M' and any(t.get('k')==2 for t in n['terms']))
            term=next(t for t in n['terms'] if t.get('k')==2)
            if fault=='basis':term['b']=term['a']
            elif fault=='K':term['k']=1
            elif fault=='coefficient':term['coefficient']+=1
            elif fault=='output':bad['graph']['primitive_outputs'].pop(next(iter(bad['graph']['primitive_outputs'])))
            elif fault=='order':bad['graph']['operations'].reverse()
            elif fault=='source':bad['operand_cover']['source_sha256']='0'*64
            else:bad['operand_cover']['selected'].append('constant:65536')
            with self.subTest(fault=fault),self.assertRaises(ValueError):verify(bad)
        p=plan(good,actors,1000,q,scalar,width=1,operand_contract=contract(q))
        bad=deepcopy(p);term=next(e for e in bad['events'] if e['op']=='ROW_M_TERM' and e['k']==2);term['k']=1
        with self.assertRaises(ValueError):replay(good,bad,{('x',i):32768 for i in range(3)}|{('y',i):-65537 for i in range(3)}|{('one',0):1})


if __name__=='__main__':unittest.main()
