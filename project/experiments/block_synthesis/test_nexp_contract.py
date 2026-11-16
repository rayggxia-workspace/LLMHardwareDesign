"""Relative EXP must lower to the same semantics as the vector oracle."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from streaming_ir import compile_graph,counts
from primitive_stages import lower
from verify_primitive_cost import verify
from test_dot_cache import example


def fixture():
    hardware=deepcopy(example()['hardware'])
    hardware['leaf_inventory']['norm_unit']={'macros':['N'],'site':'norm.S','io_resource':'norm.IO',
        'io_read_ticks':3,'io_write_ticks':3,'memory_group':0}
    hardware['sites']['norm.S']={'words':64}
    hardware['resources'].update({'norm.IO':1,'norm_unit.N':1,'norm_unit.N.context':1,'norm_unit.LC.service':1})
    for direction in ('read','write'):hardware['nets']['norm_unit.N.'+direction]={'cost':1,'fixed':False}
    model={'values':{'x':{'shape':[4]},'y':{'shape':[4]}},
        'tasks':[{'id':'kernel','op':'RelativeExp','inputs':['x'],'outputs':['y']}]}
    program={'instructions':[{'id':'exp','kernel':'kernel','op':'NExp','inputs':['x'],
        'shape':[4],'bits':32,'exponent':-15,'attributes':{}}],
        'outputs':{'y':'exp'},'initial_formats':{'x':{'bits':16}}}
    with patch('streaming_ir.duration',return_value=1):
        return compile_graph(model,hardware,[{'id':'kernel','shape':[4],'exponent':-15}],{},program)


class TestNExpContract(unittest.TestCase):
    def test_two_real_stats_reads_and_staged_audit(self):
        ir=fixture()
        work=counts(ir['program'][0]['body'],ir['native_templates'])
        self.assertEqual((work['N:commands'],work['N:read'],work['N:write']),(20,12,4))
        for candidate in (ir,lower(deepcopy(ir))):
            with patch('verify_primitive_cost.duration',return_value=1):self.assertTrue(verify(candidate)['passed'])

    def test_old_count_one_program_and_reordered_commands_rejected(self):
        ir=fixture()
        for mutation in ('missing-zero','wrong-order','packed-count-two'):
            bad=deepcopy(ir);body=bad['program'][0]['body']['sequence'][0]['body']['sequence']
            if mutation=='missing-zero':body.pop(2)
            elif mutation=='wrong-order':body[2],body[3]=body[3],body[2]
            else:bad['native_templates']['n_soft_stats']['parameters']['count']=2
            with patch('verify_primitive_cost.duration',return_value=1):
                with self.assertRaisesRegex(ValueError,'NExp'):verify(bad)

    def test_zero_identity_and_operand_sources_checked_independently(self):
        ir=fixture()
        for mutation in ('constant','source','abi'):
            bad=deepcopy(ir)
            if mutation=='constant':bad['native_constants']['0']['low32_raw_bits']=65535
            elif mutation=='source':bad['native_templates']['n_soft_zero_stats']['operand_source']='primitive_input_0.low_s16'
            else:bad['native_call_abi'].pop('nexp')
            with patch('verify_primitive_cost.duration',return_value=1):
                with self.assertRaisesRegex(ValueError,'NExp'):verify(bad)


if __name__=='__main__':unittest.main()
