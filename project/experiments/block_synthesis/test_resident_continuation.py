from copy import deepcopy
import unittest
import numpy as np

from full_integer import Q
from native_pointwise import bind_external,execute,lower
from resident_bindings import uniform_contract,variants_for
from resident_continuation import compile_loop,program_index,totals
from resident_loop_replay import Execution,element
from resident_records import plan
from resident_replay import replay
from test_resident_bindings import fixture
from test_resident_records import e_graph
from resident_probe import fixture_program
from verify_resident_bindings import verify as verify_bindings
from verify_resident_continuation import verify
from wide_program import execute as execute_original


def loop_fixture(count=19):
    ir,timing=fixture();p=ir['primitive_program']
    for f in list(p['initial_formats'].values())+p['instructions']:
        if f['shape']:f['shape']=[count]
    ir['external_regions']={n:{'address_words':i*64,'words':count if f['shape'] else 1}
                            for i,(n,f) in enumerate(p['initial_formats'].items())}
    ir['primitive_regions']={n['id']:{'address_words':200+i*32,'words':count}
                             for i,n in enumerate(p['instructions'])}
    for i,row in enumerate(ir['program']):row['temporary_external_region']['address_words']=2000+64*i
    ir['required_external_bytes']=65536
    names=[n['id'] for n in p['instructions']]
    graph=bind_external(lower(p,names,0),ir);loop=uniform_contract(ir,names)
    actors={'matrix':{'kind':'M','words':64,'stride':8,'load_ticks':20,'store_ticks':22},
            'vector':{'kind':'E','words':64,'stride':1,'load_ticks':20,'store_ticks':22}}
    return ir,timing,graph,loop,actors


class TestResidentContinuation(unittest.TestCase):
    def test_cold_prefix_cycle_cost_and_real_changed_elements(self):
        ir,q,g,loop,actors=loop_fixture(19)
        seq=compile_loop(g,loop,actors,1000,width=4,service_timing=q)
        checked=verify(g,loop,seq,actors,1000,q)
        self.assertEqual(sum(checked['program_visits']),19)
        self.assertIsNotNone(seq['cycle_start'])
        r={'graph':g,'loop':loop,'plan':seq['programs'][0],'continuation_loop':seq}
        session=None;words=cost=0
        for index in range(19):
            graph,body=element(r,index);inputs={('x',index):-2147483648+index,('y',index):2147483647-index}
            actual=replay(graph,body,inputs,session=session,return_session=True);session=actual['session']
            gold=execute(graph,inputs)
            self.assertEqual(actual['observed_native_outputs'],{n['output']:gold[n['output']] for n in graph['operations']})
            words+=actual['external_words'];cost+=body['total_ticks']
        self.assertEqual(words,seq['totals']['external_words']);self.assertEqual(cost,seq['totals']['total_ticks'])
        cold=plan(g,actors,1000,width=4,service_timing=q)
        self.assertLess(words,19*cold['external_words'])
        self.assertLess(seq['totals']['total_ticks'],19*cold['total_ticks'])
        self.assertTrue(all(e['wait_ack'] for p in seq['programs'] for e in p['events'] if e['op']=='STORE'))
        for index in (0,1,8,18):self.assertLess(program_index(seq,index),len(seq['programs']))

    def test_predecessor_source_memory_padding_and_bank_are_not_assumed(self):
        ir,q,g,loop,actors=loop_fixture();seq=compile_loop(g,loop,actors,1000,width=4,service_timing=q)
        r={'graph':g,'loop':loop,'plan':seq['programs'][0],'continuation_loop':seq}
        g0,p0=element(r,0);g1,p1=element(r,1)
        previous=replay(g0,p0,{('x',0):1,('y',0):2},return_session=True)['session']
        with self.assertRaisesRegex(ValueError,'predecessor'):replay(g1,p1,{('x',1):3,('y',1):4})
        initial=p1['initial_continuation']['actors'];tested=set()
        for actor,row in initial.items():
            for at,key in enumerate(row['slots']):
                if key is None:continue
                broken=deepcopy(previous);broken['memory'][actor][at*actors[actor]['stride']]^=1
                with self.assertRaisesRegex(ValueError,'SRAM value'):replay(g1,p1,{('x',1):3,('y',1):4},session=broken)
                broken=deepcopy(previous);broken['identities'][key]=('wrong-address',)
                with self.assertRaisesRegex(ValueError,'source identity'):replay(g1,p1,{('x',1):3,('y',1):4},session=broken)
                tested.add('record');break
            if row['padding']:
                broken=deepcopy(previous);broken['memory'][actor][row['padding'][0]*8+1]=99
                with self.assertRaisesRegex(ValueError,'padding'):replay(g1,p1,{('x',1):3,('y',1):4},session=broken)
                tested.add('padding')
            if row['bank'] is not None:
                broken=deepcopy(previous);broken['banks'][actor]=(row['bank'],99)
                with self.assertRaisesRegex(ValueError,'bank'):replay(g1,p1,{('x',1):3,('y',1):4},session=broken)
                tested.add('bank')
        self.assertTrue({'record','padding'}<=tested)
        # A matching symbolic key does not make a different array index reusable.
        e=e_graph([('fixed','varying')],{'n0'});a={'E':{'kind':'E','words':3,'stride':1,'load_ticks':3,'store_ticks':5}}
        cold=plan(e,a,0,persistent=['fixed']);s=replay(e,cold,{('fixed',0):1,('varying',0):2},return_session=True)['session']
        warm=plan(e,a,0,persistent=['fixed'],initial=cold['continuation'])
        changed=deepcopy(e);changed['objects']['fixed']['index']=1
        with self.assertRaisesRegex(ValueError,'identity changed'):
            replay(changed,warm,{('fixed',1):1,('varying',0):3},session=s)
        with self.assertRaisesRegex(ValueError,'read-only'):
            plan(e,a,0,persistent=['n0'])

    def test_sequence_rejects_free_warm_start_bad_cycle_or_missing_tail(self):
        ir,q,g,loop,actors=loop_fixture();seq=compile_loop(g,loop,actors,1000,width=4,service_timing=q)
        bad=deepcopy(seq);bad['programs'][0]['initial_continuation']=bad['programs'][-1]['continuation']
        with self.assertRaisesRegex(ValueError,'predecessor'):verify(g,loop,bad,actors,1000,q)
        bad=deepcopy(seq);bad['totals']['total_ticks']-=1
        with self.assertRaisesRegex(ValueError,'totals'):verify(g,loop,bad,actors,1000,q)
        bad=deepcopy(seq);bad['cycle_start']=None
        with self.assertRaisesRegex(ValueError,'truncated'):verify(g,loop,bad,actors,1000,q)
        bad=deepcopy(seq);bad['persistent_records'].append(next(n['output'] for n in g['operations']))
        with self.assertRaisesRegex(ValueError,'invariant'):verify(g,loop,bad,actors,1000,q)
        with self.assertRaisesRegex(ValueError,'did not close'):compile_loop(g,loop,actors,1000,max_programs=1)
        short={**loop,'elements':1};one=compile_loop(g,short,actors,1000,width=4,service_timing=q)
        verify(g,short,one,actors,1000,q);self.assertIsNone(one['cycle_start'])

    def test_b_bank_reuse_requires_the_actual_previous_bank(self):
        p=fixture_program();p['instructions']=p['instructions'][2:3]
        p['instructions'][0]['inputs']=['x'];p['initial_formats']['x']['bits']=16
        g=lower(p,['s'])
        for i,o in enumerate(g['objects'].values()):o['external_address']=100+64*i
        actors={'P':{'kind':'M','words':32,'stride':8,'load_ticks':3,'store_ticks':5}}
        loop={'elements':11,'sources':{'x':'element'}}
        seq=compile_loop(g,loop,actors,0,width=4)
        r={'graph':g,'loop':loop,'plan':seq['programs'][0],'continuation_loop':seq}
        g0,p0=element(r,0);g1,p1=element(r,1)
        self.assertTrue(next(e for e in p1['events'] if e['op']=='M_TERM')['reuse_b'])
        session=replay(g0,p0,{('x',0):-32768},return_session=True)['session']
        replay(g1,p1,{('x',1):32767},session=session)
        session['banks'].clear()
        with self.assertRaisesRegex(ValueError,'B bank'):replay(g1,p1,{('x',1):32767},session=session)

    def test_two_body_cycle_charges_the_actual_tail_and_all_loads(self):
        g=e_graph([('a','b')],{'n0'});actors={'E':{'kind':'E','words':3,'stride':1,'load_ticks':3,'store_ticks':5}}
        loop={'elements':8,'sources':{'a':'scalar','b':'scalar'}}
        seq=compile_loop(g,loop,actors,0,width=4)
        # Two legal bodies have the same memory postcondition, but one
        # explicitly reloads a read-only word. This tests a nonuniform cycle
        # and an incomplete final turn without relying on planner symmetry.
        warm=seq['programs'][-1];extra=deepcopy(warm)
        at=extra['initial_continuation']['actors']['E']['slots'].index('a')
        extra['events'].insert(0,{'op':'LOAD','actor':'E','address':at,'record':'a',
                                 'external_address':g['objects']['a']['external_address'],'wait_ack':True})
        for field in ('external_load_words','external_words'):extra[field]+=1
        for field in ('copy_ticks','total_ticks'):extra[field]+=3
        seq.update(programs=[seq['programs'][0],warm,extra],cycle_start=1);seq['totals']=totals(seq)
        checked=verify(g,loop,seq,actors,0,None)
        self.assertEqual(checked['program_visits'],[1,4,3])
        session=None;words=0
        for index in range(8):
            body=seq['programs'][program_index(seq,index)]
            out=replay(g,body,{('a',0):1,('b',0):2},session=session,return_session=True)
            session=out['session'];words+=out['external_words']
        self.assertEqual(words,seq['totals']['external_words'])

    def test_common_pool_and_every_element_integer_replacement(self):
        ir,q,g,loop,actors=loop_fixture(7);old=deepcopy(ir['tasks']);variants_for(ir,q,width=4,continuation=True)
        self.assertEqual(ir['tasks'],old);verify_bindings(ir)
        warm=[r for r in ir['resident_recipes'].values() if r.get('continuation_loop')]
        self.assertEqual(len(warm),5)
        r=min(warm,key=lambda r:r['continuation_loop']['totals']['total_ticks'])
        p=deepcopy(ir['primitive_program']);p['outputs']={n['id']:n['id'] for n in p['instructions']}
        initial={'x':Q(np.asarray([-2147483648,2147483647,-32769,32768,0,1,-1],dtype=np.int64),0),
                 'y':Q(np.asarray([32767,-32768,2147483647,-1,1,0,32768],dtype=np.int64),0),
                 'one':Q(np.asarray(1,dtype=np.int64),0)}
        gold=execute_original(p,initial,[],None);backend=Execution(p,[r])
        actual=execute_original(p,initial,[],None,region_executor=backend)
        for name in gold:np.testing.assert_array_equal(actual[name].raw,gold[name].raw)
        self.assertEqual(backend.report()['loops'][0]['external_words'],r['continuation_loop']['totals']['external_words'])


if __name__=='__main__':unittest.main()
