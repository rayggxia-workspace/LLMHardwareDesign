from copy import deepcopy
import unittest

from resident_batch import plan
from resident_operand_contract import validate
from test_resident_batch import case
from verify_resident_batch import replay
from native_pointwise import execute


def contract(rows):
    # Artificial admission receipt for algorithm tests, not RTL evidence.
    return {'kind':'native-resident-services-active-prefix-v1','rtl_sha256':deepcopy(rows['rtl_sha256']),
        'profile':deepcopy(rows['profile']),
        'proof':{'manifest_sha256':'a'*64,'logs_sha256':[str(i)*64 for i in range(4)],'cases_per_initialization':[1]*4},
        'operand_mask':{'kind':'native-M-active-prefix-v1','padding_writes':False,
            'initializations':['zero','ones','mixed','unknown'],'rows':[1,8],'k':[1,2],'columns':1}}


class TestResidentOperandMask(unittest.TestCase):
    def test_active_prefix_has_real_traffic_savings_and_old_contract_survives(self):
        _,tile,actors,q,scalar=case(simple=True);values={('x',0):-32768,('x',1):32767,('y',0):7,('y',1):-9}
        old=plan(tile,actors,0,q,scalar,width=None)
        new=plan(tile,actors,0,q,scalar,width=None,operand_contract=contract(q))
        self.assertTrue(replay(tile,old,values)['passed']);self.assertTrue(replay(tile,new,values)['passed'])
        self.assertLess(new['total_ticks'],old['total_ticks']);self.assertLess(new['external_words'],old['external_words'])
        self.assertFalse(any(e['op']=='LOAD_ZERO' for e in new['events']))
        self.assertTrue(any(e['op']=='LOAD_ZERO' for e in old['events']))
        bad=deepcopy(new);bad.pop('operand_contract')
        with self.assertRaises(ValueError):replay(tile,bad,values)

    def test_partial_overwrites_preserve_real_values_and_exact_S32_work(self):
        _,tile,actors,q,scalar=case();proof=contract(q)
        candidates=[plan(tile,actors,1000,q,scalar,width=w,schedule=schedule,operand_contract=proof)
                    for w,schedule in ((1,'fixed'),(2,'fixed'),(1,'ready'),(2,'ready'))]
        for edge in (-2147483648,-32769,0,32768,2147483647):
            values={('x',i):edge for i in range(3)}|{('y',i):(-32769,32768,-1)[i] for i in range(3)}|{('one',0):1}
            for p in candidates:
                got=replay(tile,p,values)['observed_native_outputs']
                for rr,g in enumerate(tile['graphs']):
                    expected=execute(g,values)
                    for primitive,key in g['primitive_outputs'].items():
                        self.assertEqual(got[tile['graph']['primitive_outputs'][f'{rr}:{primitive}']],expected[key])
                self.assertEqual(p['copy_ticks'],3*p['external_load_words']+5*p['external_store_words'])

    def test_mask_proof_does_not_waive_active_operands_or_alignment(self):
        _,tile,actors,q,scalar=case(simple=True)
        good=plan(tile,actors,0,q,scalar,width=2,operand_contract=contract(q));values={('x',0):3,('x',1):-7}
        for fault in ('active-data','alignment','output','bill','proof','rtl','profile'):
            bad=deepcopy(good)
            if fault=='active-data':bad['events'].remove(next(e for e in bad['events'] if e['op']=='LOAD'))
            elif fault=='alignment':next(e for e in bad['events'] if e['op']=='ROW_M_TERM')['a']+=1
            elif fault=='output':bad['events'].remove(next(e for e in bad['events'] if e['op']=='STORE_COMMIT'))
            elif fault=='bill':bad['total_ticks']-=1
            elif fault=='proof':bad['operand_contract']['proof']['logs_sha256'][3]=bad['operand_contract']['proof']['logs_sha256'][0]
            elif fault=='rtl':bad['operand_contract']['rtl_sha256']={'other':'RTL'}
            else:next(iter(bad['operand_contract']['profile']['P'].values()))['0']+=1
            with self.subTest(fault=fault),self.assertRaises(ValueError):replay(tile,bad,values)
        with self.assertRaises(ValueError):validate({'kind':'not-qualified'},q)


if __name__=='__main__':unittest.main()
