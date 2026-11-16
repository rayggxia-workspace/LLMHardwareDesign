from copy import deepcopy
from types import SimpleNamespace
import unittest

from cover_frontier import search
from resident_bindings import digest,variants_for as resident
from resident_overlap_bindings import variants_for
from test_loop_dp import binding
from test_resident_bindings import fixture
from transition import evaluate_transition
from verify_cover_frontier import verify as verify_schedule
from verify_resident_bindings import verify


class TestResidentOverlapBindings(unittest.TestCase):
    def test_source_qualified_pool_retains_serial_programs_and_checks_rebinding(self):
        ir,q=fixture();resident(ir,q,width=2,value_reuse=True,continuation=True)
        old=deepcopy(ir['resident_actions']);recipes=deepcopy(ir['resident_recipes'])
        variants_for(ir,width=4)
        self.assertEqual(ir['resident_recipes'],recipes)
        for action,original in zip(ir['resident_actions'],old):
            self.assertEqual(action['bindings'][:len(original['bindings'])],original['bindings'])
        self.assertGreater(ir['resident_overlap_scope']['added_bindings'],0)
        self.assertGreater(ir['resident_overlap_scope']['schedule_cache_hits'],0)
        self.assertTrue(verify(ir)['passed'])
        chosen=next(b for a in ir['resident_actions'] for b in a['bindings'] if b.get('resident_overlap'))
        bad=deepcopy(ir)
        forged=next(b for a in bad['resident_actions'] for b in a['bindings'] if b['id']==chosen['id'])
        forged['ticks']-=1
        with self.assertRaisesRegex(ValueError,'work/resources'):verify(bad,numeric=False)
        bad=deepcopy(ir);bad['hardware']['leaf_inventory']['matrix']['memory_group']+=1
        with self.assertRaisesRegex(ValueError,'channels'):verify(bad,numeric=False)
        bad=deepcopy(ir);oldkey=chosen['resident_overlap']['proof'];p=bad['resident_overlap_proofs'].pop(oldkey)
        p['visits'][0]+=1;newkey=digest(p);bad['resident_overlap_proofs'][newkey]=p
        for a in bad['resident_actions']:
            for b in a['bindings']:
                if b.get('resident_overlap',{}).get('proof')==oldkey:b['resident_overlap']['proof']=newkey
        with self.assertRaisesRegex(ValueError,'visits'):verify(bad,numeric=False)

    def test_outer_schedule_reserves_both_actors_and_channel_until_final_ack(self):
        # Unit reservation certificate only. Native proof validity is covered
        # above; this checks integration with the real common frontier.
        h={'resources':{'M':1,'E':1,'channel':1},'sites':{'MS':{'words':32},'ES':{'words':8}},'nets':{}}
        b={**binding('overlap','M',10),'resources':['M','E','channel'],'site':'MS','scratch_words':32,
           'scratch_by_site':{'MS':32,'ES':8},'resident_region':{'kind':'serial-native-resident-loop-v1',
            'invalidate_read_cache':['ES','MS']},'resident_overlap':{'kind':'commuting-native-actors-v1',
            'proof':'unit-certificate','reservation':'all-union-resources-through-final-ACK'}}
        tasks=[{'id':'a','bindings':[{**binding('old','M',100),'site':'MS'}]},
               {'id':'b','after':['a'],'bindings':[{**binding('old','M',100),'site':'MS'}]},
               {'id':'outside','bindings':[{**binding('E','E',7),'site':'ES'}]}]
        covers=[{'id':'f','covers':['a','b'],'bindings':[b]}]
        plan=search(tasks,h,covers,width=None)
        self.assertEqual(plan['makespan'],17)
        self.assertTrue(verify_schedule(tasks,h,covers,plan)['passed'])
        inside=next(r for r in plan['tasks'] if r['id']=='f');outside=next(r for r in plan['tasks'] if r['id']=='outside')
        self.assertTrue(inside['end']<=outside['start'] or outside['end']<=inside['start'])
        state=SimpleNamespace(resources={'M':(0,),'E':(20,),'channel':(5,)},cache={'MS':('x',1,2)},makespan=20,nets=frozenset())
        ev=evaluate_transition(state,b,h,3,retention='invalidate')
        self.assertEqual((ev['start'],ev['end']),(20,30));self.assertEqual(ev['cache'],{})
        bad=deepcopy(b);bad['resident_overlap']['reservation']='partial'
        self.assertFalse(evaluate_transition(state,bad,h,3,retention='invalidate')['legal'])


if __name__=='__main__':unittest.main()
