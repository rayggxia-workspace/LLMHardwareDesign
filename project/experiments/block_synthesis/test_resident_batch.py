from copy import deepcopy
import random
import unittest

from native_pointwise import bind_external,execute,lower
from resident_batch import plan
from resident_batch_graph import build,units,verify
from verify_resident_batch import replay
from test_native_pointwise import node,reference,signed32
from test_resident_bindings import fixture


def qualification(scalar,rows=3):
    # Artificial cost table for algorithm tests, never hardware evidence.
    return {'kind':'native-resident-row-services-v1','rtl_sha256':scalar['rtl_sha256'],
        'proof':{'logs_sha256':['unit-0','unit-1','unit-2'],'cases_per_initialization':[1]*3},
        'formats':[[w,s] for w in (16,32) for s in range(64)],
        'profile':{'P':{str(r):{'0':4,'1':14+10*r,'2':14+10*r,
            **{str(64+c*64+s):12 for c in (1,2) for s in range(64)}} for r in range(1,rows+1)},
            'feeder':{str(r):{'0':11+2*r,'1':7+2*r} for r in range(1,rows+1)}}}


def case(simple=False,dependent_b=False):
    ir,scalar=fixture();p=ir['primitive_program']
    if simple:
        p={'instructions':[node('a','Product' if dependent_b else 'Convert',['x','y'] if dependent_b else ['x'],shape=(2,),bits=32,shift=0)],
           'outputs':{'out':'a'},'initial_formats':{'x':{'bits':16,'shape':[2]},'y':{'bits':16,'shape':[2]}}}
    graphs=[];size=2 if simple else 3;addresses={};cursor=10
    for i in range(size):
        if simple:
            g=lower(p,[n['id'] for n in p['instructions']],i)
            for key,o in g['objects'].items():
                identity=(o['kind'],o.get('tensor'),o.get('index'),o.get('literal'),key if o['kind']=='produced' else None)
                if o['kind']=='produced':o['external_address']=100+i
                else:
                    if identity not in addresses:addresses[identity]=cursor;cursor+=1
                    o['external_address']=addresses[identity]
        else:g=bind_external(lower(p,[n['id'] for n in p['instructions']],i),ir)
        graphs.append(g)
    tile=build(graphs,scratch_start=1250,external_capacity_words=3000,max_rows=3)
    actors={'P':{'kind':'M','site':'P.S','words':16 if simple else 64,'stride':8,'load_ticks':3,'store_ticks':5},
            'E':{'kind':'E','site':'E.S','words':8,'stride':1,'load_ticks':3,'store_ticks':5}}
    return p,tile,actors,qualification(scalar),scalar


class TestResidentBatch(unittest.TestCase):
    def test_layout_lookahead_remains_heuristic_under_width_one(self):
        _,_,actors,q,scalar=case(simple=True)
        p={'instructions':[node('a','Convert',['x'],shape=(2,),bits=16,shift=0),
                           node('b','Product',['a','y'],shape=(2,),bits=16,shift=0)],
           'outputs':{'out':'b'},'initial_formats':{'x':{'bits':16,'shape':[2]},'y':{'bits':16,'shape':[2]}}}
        graphs=[];addresses={};cursor=10
        for row in range(2):
            g=lower(p,['a','b'],row)
            for key,o in g['objects'].items():
                if o['kind']=='produced':o['external_address']=100+10*int(key.split(':')[1])+row
                else:
                    identity=(o['kind'],o.get('tensor'),o.get('index'),o.get('literal'))
                    if identity not in addresses:addresses[identity]=cursor;cursor+=1
                    o['external_address']=addresses[identity]
            graphs.append(g)
        tile=build(graphs,scratch_start=1250,external_capacity_words=3000,max_rows=3)
        actors['P']['words']=32
        for a in actors.values():a.update(load_ticks=40,store_ticks=42)
        values={('x',0):15,('x',1):-18,('y',0):7,('y',1):-9}
        plans={rank:plan(tile,actors,0,q,scalar,width=1,rank_policy=rank)
               for rank in ('future_copies','future_layout')}
        exact=plan(tile,actors,0,q,scalar,width=None,rank_policy='future_layout')
        for candidate in (*plans.values(),exact):self.assertTrue(replay(tile,candidate,values)['passed'])
        # A tighter optimistic bound need not improve width-one choices; the
        # preserved case actually makes that greedy result worse. Exhaustive
        # finite-family results must remain independent of ranking policy.
        other=plan(tile,actors,0,q,scalar,width=None,rank_policy='future_copies')
        self.assertEqual(other['total_ticks'],exact['total_ticks'])
        for candidate in plans.values():self.assertGreaterEqual(candidate['total_ticks'],exact['total_ticks'])

    def test_real_layout_and_command_savings_against_same_action_serial(self):
        p,tile,actors,q,scalar=case(simple=True);values={('x',0):-32768,('x',1):32767,('y',0):3,('y',1):4}
        serial=plan(tile,actors,0,q,scalar,width=None,allow_batch=False)
        batch=plan(tile,actors,0,q,scalar,width=None,allow_batch=True)
        for candidate in (serial,batch):
            result=replay(tile,candidate,values)
            self.assertTrue(result['passed'])
            for row,g in enumerate(tile['graphs']):
                gold=execute(g,values)
                for primitive,record in g['primitive_outputs'].items():
                    canonical=tile['graph']['primitive_outputs'][f'{row}:{primitive}']
                    self.assertEqual(result['observed_native_outputs'][canonical],gold[record])
        self.assertLess(batch['total_ticks'],serial['total_ticks'])
        self.assertEqual(sum(e['op']=='ROW_M_TERM' for e in batch['events']),1)
        self.assertEqual(sum(e['op']=='ROW_M_TERM' for e in serial['events']),2)
        self.assertEqual([e['address'] for e in batch['events'] if e['op']=='ROW_M_FINAL'],[0,1])

    def test_different_B_identity_is_not_batched_even_when_numbers_match(self):
        p,tile,actors,q,scalar=case(simple=True,dependent_b=True)
        self.assertFalse(units(tile)[0]['batchable'])
        candidate=plan(tile,actors,0,q,scalar,width=4)
        values={('x',0):8,('x',1):-9,('y',0):3,('y',1):3}
        self.assertTrue(replay(tile,candidate,values)['passed'])
        self.assertTrue(all(e['rows']==1 for e in candidate['events'] if e['op']=='ROW_M_TERM'))

    def test_complete_S32_preparation_and_cross_store_roundtrips_are_paid(self):
        p,tile,actors,q,scalar=case();rng=random.Random(220201)
        plans=[plan(tile,actors,1000,q,scalar,width=w,allow_batch=b) for w,b in ((1,False),(1,True),(4,True))]
        plans.append(plan(tile,actors,1000,q,scalar,width=4,rank_policy='future_layout'))
        for candidate in plans:self.assertEqual(candidate['status'],'planned')
        for trial in range(7):
            edge=(-2147483648,2147483647,-32769,32768,0,1,-1)[trial]
            initial={'x':[edge,rng.randrange(-(1<<31),1<<31),-1],
                     'y':[rng.randrange(-(1<<31),1<<31) for _ in range(3)],'one':[1]}
            values={(name,i):v for name,row in initial.items() for i,v in enumerate(row)}
            for candidate in plans:
                result=replay(tile,candidate,values);observed=result['observed_native_outputs']
                for row,g in enumerate(tile['graphs']):
                    expected=reference(p,initial,row)
                    for primitive in g['primitive_outputs']:
                        key=tile['graph']['primitive_outputs'][f'{row}:{primitive}']
                        self.assertEqual(signed32(observed[key]),expected[primitive])
        # No zero-cost P/E delivery: produced values crossing stores are
        # physically STORE-ACKed and LOAD-ACKed, even if their tags are known.
        candidate=plans[-1];stored=set();cross=0
        for e in candidate['events']:
            if e['op'] in ('STORE','STORE_COMMIT'):stored.add((e['record'],e['actor']))
            if e['op']=='LOAD' and tile['graph']['objects'][e['record']]['kind']=='produced':
                self.assertTrue(any(value==e['record'] for value,actor in stored));cross+=1
        self.assertGreater(cross,0)
        self.assertEqual(candidate['copy_ticks'],3*candidate['external_load_words']+5*candidate['external_store_words'])

    def test_independent_checker_rejects_bad_geometry_backing_output_and_cost(self):
        p,tile,actors,q,scalar=case(simple=True);candidate=plan(tile,actors,0,q,scalar,width=4)
        values={('x',0):5,('x',1):-7,('y',0):2,('y',1):3}
        for fault in ('alignment','B-bank','early-final','missing-guard','wrong-row','missing-commit','underbill'):
            bad=deepcopy(candidate)
            if fault=='alignment':next(e for e in bad['events'] if e['op']=='ROW_M_TERM')['a']+=1
            elif fault=='B-bank':next(e for e in bad['events'] if e['op']=='ROW_M_TERM')['reuse_b']=True
            elif fault=='early-final':next(e for e in bad['events'] if e['op']=='ROW_M_FINAL')['wait_s_ack']=False
            elif fault=='missing-guard':bad['events'].remove(next(e for e in bad['events'] if e['op']=='LOAD_ZERO'))
            elif fault=='wrong-row':next(e for e in reversed(bad['events']) if e['op']=='ROW_M_FINAL')['row']=0
            elif fault=='missing-commit':bad['events'].remove(next(e for e in bad['events'] if e['op']=='STORE_COMMIT'))
            else:bad['total_ticks']-=1
            with self.subTest(fault=fault),self.assertRaises(ValueError):replay(tile,bad,values)

    def test_batch_source_and_finite_scratch_are_not_assumed(self):
        p,tile,actors,q,scalar=case()
        self.assertTrue(verify(tile)['passed']);self.assertGreater(tile['scratch_words'],0)
        with self.assertRaisesRegex(ValueError,'capacity'):
            build(tile['graphs'],scratch_start=1250,external_capacity_words=1251,max_rows=3)
        bad=deepcopy(tile);next(o for o in bad['graph']['objects'].values() if o['kind']=='produced')['external_address']=0
        with self.assertRaises(ValueError):verify(bad)
        bad=deepcopy(tile);bad['groups'][0].reverse()
        with self.assertRaises(ValueError):verify(bad)
        bad=deepcopy(q);bad['rtl_sha256']={'different':'RTL'}
        with self.assertRaisesRegex(ValueError,'RTL'):plan(tile,actors,1000,bad,scalar)
        # Removing row-3 service evidence retains the scalar fallback.
        bad=deepcopy(q);bad['profile']['P'].pop('3')
        candidate=plan(tile,actors,1000,bad,scalar,width=1)
        self.assertTrue(all(e['rows']!=3 for e in candidate['events'] if e['op']=='ROW_M_TERM'))


if __name__=='__main__':unittest.main()
