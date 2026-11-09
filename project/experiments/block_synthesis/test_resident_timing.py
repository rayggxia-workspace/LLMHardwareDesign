from copy import deepcopy
import unittest

from native_pointwise import execute
from resident_records import plan
from resident_replay import replay
from resident_timing import audit,event_ticks,validate


def graph():
    objects={x:{'kind':'external','tensor':x,'index':0,'bits':32,'external_address':100+i}
             for i,x in enumerate(('a','b','c'))}
    operations=[]
    for i,b in enumerate(('b','c','b')):
        name='n'+str(i);objects[name]={'kind':'produced','external_address':200+i}
        operations.append({'id':name,'kind':'M','inputs':['a',b],'output':name,'k':1,
            'terms':[{'a':'a','b':b,'coefficient':1,'scale_shift':0}],'width':32,'shift':0})
    return {'objects':objects,'operations':operations,'live_out':{'out':'n2'},
            'primitive_outputs':{n['id']:n['output'] for n in operations}}


def timing():
    # Synthetic heterogeneous copy/service weights test the algorithm. They
    # are not accepted hardware measurements or a reported speedup.
    return {'kind':'native-resident-services-v1','proof':{'fixture':True},'rtl_sha256':{'fixture':'unit'},
            'profile':{'P':{'0':4,'2':24,'144':12},'E':{'37':20},'feeder':{'0':1000,'1':1}}}


class TestResidentTiming(unittest.TestCase):
    def test_actual_total_cost_can_choose_another_bank_owner(self):
        g=graph();actors={n:{'kind':'M','words':16,'stride':8,'load_ticks':1,'store_ticks':1}
                         for n in ('M0','M1')}
        copy_only=plan(g,actors,0,width=1)
        timed=plan(g,actors,0,width=8,service_timing=timing())
        old_time=copy_only['copy_ticks']+sum(event_ticks(e,timing()) for e in copy_only['events'])
        self.assertLess(timed['total_ticks'],old_time)
        self.assertLess(sum(e['op']=='M_TERM' and not e['reuse_b'] for e in timed['events']),
                        sum(e['op']=='M_TERM' and not e['reuse_b'] for e in copy_only['events']))
        self.assertTrue(audit(timed,timing())['passed'])
        values={('a',0):7,('b',0):-9,('c',0):13};expected=execute(g,values)
        for candidate in (copy_only,timed):
            self.assertEqual(replay(g,candidate,values)['observed_native_outputs'],
                             {n['output']:expected[n['output']] for n in g['operations']})
        # Independent arithmetic accounting for this diagnostic's parameters.
        terms=[e for e in timed['events'] if e['op']=='M_TERM']
        native=len(terms)*(4+24)+sum(1 if e['reuse_b'] else 1000 for e in terms)+3*12
        self.assertEqual(timed['native_service_ticks'],native)
        self.assertEqual(timed['total_ticks'],timed['copy_ticks']+native)

    def test_unknown_profiles_and_forged_service_total_fail(self):
        g=graph();actors={'M':{'kind':'M','words':16,'stride':8,'load_ticks':1,'store_ticks':1}}
        p=plan(g,actors,0,width=8,service_timing=timing());bad=deepcopy(p);bad['native_service_ticks']-=1
        with self.assertRaisesRegex(ValueError,'accounting'):audit(bad,timing())
        bad=timing();del bad['profile']['P']['144']
        with self.assertRaisesRegex(ValueError,'unmeasured'):plan(g,actors,0,service_timing=bad)
        bad=timing();bad['profile']['feeder']['0']=0
        with self.assertRaises(ValueError):validate(bad)
        bad=deepcopy(p);bad['service_timing']['proof']={'fixture':'different'}
        with self.assertRaisesRegex(ValueError,'provenance'):audit(bad,timing())


if __name__=='__main__':unittest.main()
