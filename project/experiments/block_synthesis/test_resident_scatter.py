from copy import deepcopy
import unittest
from native_pointwise import execute
from resident_batch import plan
from test_resident_batch import case
from test_resident_operand_mask import contract
from verify_resident_batch import replay


class TestResidentScatter(unittest.TestCase):
    def test_address_choices_have_real_scalar_writes_and_preserve_outputs(self):
        _,tile,actors,q,scalar=case(simple=True);proof=contract(q)
        programs={layout:plan(tile,actors,0,q,scalar,width=None,final_layout=layout,operand_contract=proof)
                  for layout in ('contiguous','scatter','choice')}
        for edge in (-32768,-1,0,32767):
            values={('x',0):edge,('x',1):-edge if edge!=-32768 else 32767}
            for program in programs.values():self.assertTrue(replay(tile,program,values)['passed'])
        self.assertLessEqual(programs['choice']['total_ticks'],programs['contiguous']['total_ticks'])
        self.assertLessEqual(programs['choice']['total_ticks'],programs['scatter']['total_ticks'])
        finals=[e for e in programs['scatter']['events'] if e['op']=='ROW_M_FINAL']
        self.assertTrue(any(e['rows']>1 for e in finals))
        self.assertTrue(all(e['address']%8==0 and e['wait_s_ack'] for e in finals))
        self.assertEqual({e['row'] for e in finals},{0,1})
        self.assertEqual(programs['scatter']['copy_ticks'],3*programs['scatter']['external_load_words']+5*programs['scatter']['external_store_words'])

    def test_ready_and_fixed_scatter_keep_full_S32_semantics(self):
        _,tile,actors,q,scalar=case();proof=contract(q)
        programs=[plan(tile,actors,1000,q,scalar,width=2,schedule=s,final_layout='scatter',operand_contract=proof)
                  for s in ('fixed','ready')]
        for edge in (-2147483648,-32769,32768,2147483647):
            values={('x',i):edge for i in range(3)}|{('y',i):(-1,32768,-32769)[i] for i in range(3)}|{('one',0):1}
            for program in programs:
                outputs=replay(tile,program,values)['observed_native_outputs']
                for rr,g in enumerate(tile['graphs']):
                    expected=execute(g,values)
                    for key in g['primitive_outputs'].values():self.assertEqual(outputs[tile['maps'][rr][key]],expected[key])

    def test_scatter_does_not_waive_row_context_ACK_or_backing(self):
        _,tile,actors,q,scalar=case(simple=True);proof=contract(q)
        p=plan(tile,actors,0,q,scalar,width=None,final_layout='scatter',operand_contract=proof)
        for fault in ('duplicate-row','out-of-range','ack','missing-output'):
            bad=deepcopy(p);finals=[e for e in bad['events'] if e['op']=='ROW_M_FINAL']
            if fault=='duplicate-row':finals[1]['row']=finals[0]['row']
            elif fault=='out-of-range':finals[1]['address']=actors['P']['words']
            elif fault=='ack':finals[0]['wait_s_ack']=False
            else:bad['events'].remove(finals[1])
            with self.subTest(fault=fault),self.assertRaises(ValueError):replay(tile,bad,{('x',0):3,('x',1):-7})
        with self.assertRaisesRegex(ValueError,'qualification'):plan(tile,actors,0,q,scalar,final_layout='choice')


if __name__=='__main__':unittest.main()
