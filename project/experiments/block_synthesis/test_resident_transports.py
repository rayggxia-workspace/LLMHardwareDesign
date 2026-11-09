from copy import deepcopy
import unittest

from native_pointwise import execute,lower
from resident_continuation import compile_loop
from resident_loop_replay import element
from resident_probe import fixture_program
from resident_records import plan
from resident_replay import replay
from verify_resident_continuation import verify


def fixture():
    p=fixture_program();g=lower(p,[n['id'] for n in p['instructions']])
    for i,o in enumerate(g['objects'].values()):o['external_address']=1000+64*i
    actors={'P':{'kind':'M','site':'p-s','words':32,'stride':8,'load_ticks':20,'store_ticks':22},
            'U':{'kind':'E','site':'u-s','words':3,'stride':1,'load_ticks':20,'store_ticks':22}}
    paths=[{'kind':'resident-transport-candidate-v1','id':s+'-'+d,'source':s,'destination':d,
            'word_bits':128,'ticks':7,'nets':[s+'-'+d+'.bus'],'resources':[s+'.io',d+'.io','tx-'+s],
            'protocol':'reserved-sink/source-held-through-write-ack',
            'provenance':'synthetic hypothesis, no qualified product path'} for s,d in (('P','U'),('U','P'))]
    values={('x',0):-2147483648,('y',0):2147483647,('one',0):1}
    return g,actors,paths,values


class TestResidentTransports(unittest.TestCase):
    def test_exhaustive_cost_matches_hand_enumerated_two_stage_program(self):
        # One M product, then E minimum with x. Exactly two guarded M cells
        # are compulsory. Retain x, overwrite consumed y with the product,
        # transfer x and product over one static link, and commit E output.
        # This lower bound is achievable, independent of planner events.
        objects={'x':{'kind':'external','tensor':'x','index':0,'bits':16,'external_address':100},
                 'y':{'kind':'external','tensor':'y','index':0,'bits':16,'external_address':101},
                 'm':{'kind':'produced','external_address':102},'e':{'kind':'produced','external_address':103}}
        graph={'objects':objects,'operations':[
            {'id':'m','kind':'M','inputs':['x','y'],'output':'m','k':1,'width':16,'shift':0,
             'terms':[{'a':'x','b':'y','coefficient':1,'scale_shift':0}]},
            {'id':'e','kind':'E','inputs':['m','x'],'output':'e','opcode':5,'shift':0}],
            'live_out':{'out':'e'}}
        _,actors,paths,_=fixture();actors['P']['words']=16;actors['U']['words']=2
        for policy in ('copy_cost','future_copies'):
            result=plan(graph,actors,0,width=None,transports=paths,transport_net_budget=1,rank_policy=policy)
            self.assertEqual(result['copy_ticks'],2*20+2*7*20+2*7+22)
            self.assertEqual(result['external_words'],17)
            self.assertEqual(result['transport_words'],2)
            replay(graph,result,{('x',0):2,('y',0):3})

    def test_transport_is_paid_actual_s_copy_and_reduces_external_records(self):
        g,actors,paths,values=fixture();gold=execute(g,values)
        original=plan(g,actors,0,width=8)
        self.assertFalse(any(e['op']=='TRANSFER' for e in original['events']))
        for policy in ('copy_cost','future_copies'):
            result=plan(g,actors,0,width=8,transports=paths,transport_net_budget=2,rank_policy=policy)
            self.assertGreater(result['transport_words'],0)
            self.assertLess(result['external_words'],original['external_words'])
            self.assertEqual(result['transport_ticks'],7*result['transport_words'])
            actual=replay(g,result,values)
            self.assertEqual(actual['observed_native_outputs'],{n['output']:gold[n['output']] for n in g['operations']})
            self.assertTrue(all(e['record'] in g['objects'] for e in result['events'] if e['op']=='TRANSFER'))

    def test_static_union_budget_includes_both_directions_and_reuse_once(self):
        g,actors,paths,values=fixture()
        for budget in (0,1,2):
            result=plan(g,actors,0,width=16,transports=paths,transport_net_budget=budget)
            replay(g,result,values)
            used={n for e in result['events'] if e['op']=='TRANSFER' for n in next(p['nets'] for p in paths if p['id']==e['path'])}
            self.assertEqual(sorted(used),result['transport_nets']);self.assertLessEqual(len(used),budget)
            if not budget:self.assertEqual(result['transport_words'],0)
        expensive=deepcopy(paths)
        for p in expensive:p['ticks']=10000
        result=plan(g,actors,0,width=16,transports=expensive,transport_net_budget=2)
        self.assertEqual(result['transport_words'],0)

    def test_zero_budget_preserves_original_future_ranking_and_program(self):
        g,actors,paths,_=fixture()
        old=plan(g,actors,0,width=8,rank_policy='future_copies')
        candidate=plan(g,actors,0,width=8,rank_policy='future_copies',transports=paths,transport_net_budget=0)
        self.assertEqual(old['events'],candidate['events'])
        self.assertEqual(old['total_ticks'],candidate['total_ticks'])

    def test_faults_cannot_use_host_values_or_skip_destination_ack(self):
        g,actors,paths,values=fixture();result=plan(g,actors,0,width=8,transports=paths,transport_net_budget=2)
        at=next(i for i,e in enumerate(result['events']) if e['op']=='TRANSFER')
        for key,value in (('wait_ack',False),('source_hold_until_ack',False),('sink_reserved',False),
                          ('source_address',9999),('path','undeclared'),('record','fake')):
            bad=deepcopy(result);bad['events'][at][key]=value
            with self.assertRaises(ValueError):replay(g,bad,values)
        bad=deepcopy(result);del bad['events'][at]
        with self.assertRaises(ValueError):replay(g,bad,values)
        bad=deepcopy(result);bad['transport_net_budget']=0
        with self.assertRaises(ValueError):replay(g,bad,values)
        bad=deepcopy(result);bad['transport_ticks']-=1
        with self.assertRaises(ValueError):replay(g,bad,values)

    def test_loop_carries_static_union_but_not_previous_element_results(self):
        g,actors,paths,values=fixture()
        loop={'elements':9,'sources':{o['tensor']:'scalar' if 'literal' in o else 'element'
                                    for o in g['objects'].values() if o['kind']=='external'}}
        seq=compile_loop(g,loop,actors,0,width=8,transports=paths,transport_net_budget=1)
        verify(g,loop,seq,actors,0,None);session=None
        recipe={'graph':g,'loop':loop,'plan':seq['programs'][0],'continuation_loop':seq}
        observed_transfers=0
        for i in range(loop['elements']):
            graph,program=element(recipe,i)
            actual_values={(o['tensor'],o['index']):(1 if 'literal' in o else (-1 if i%2 else 1)*32767)
                           for o in graph['objects'].values() if o['kind']=='external'}
            actual=replay(graph,program,actual_values,session=session,return_session=True);session=actual['session']
            expected=execute(graph,actual_values)
            self.assertEqual(actual['observed_native_outputs'],{n['output']:expected[n['output']] for n in graph['operations']})
            observed_transfers+=program['transport_words']
            self.assertLessEqual(len(program['transport_nets']),1)
        self.assertEqual(observed_transfers,seq['totals']['transport_words'])

    def test_invalid_catalog_and_phantom_initial_nets_rejected(self):
        g,actors,paths,values=fixture()
        for key,value in (('ticks',0),('word_bits',64),('destination','missing'),('nets',[]),('provenance','')):
            bad=deepcopy(paths);bad[0][key]=value
            with self.assertRaises(ValueError):plan(g,actors,0,transports=bad)
        result=plan(g,actors,0,width=1,transports=paths)
        bad=deepcopy(result['continuation']);bad['transport_nets']=['phantom']
        with self.assertRaisesRegex(ValueError,'static transport'):plan(g,actors,0,transports=paths,initial=bad)


if __name__=='__main__':unittest.main()
