import unittest
from streaming_ir import counts,repeat,call,seq,compile_graph
from loop_dp import search
from verify_loop_dp import verify
from unittest.mock import patch
from copy import deepcopy
from verify_primitive_cost import verify as verify_cost


class StreamingTests(unittest.TestCase):
    def test_finite_symbolic_count(self):
        # A billion repetitions stay one finite loop in the IR.
        lib={'x':{'macro':'M','read_words':2,'write_words':1,'ticks':4,'native':'M'}}
        got=counts(repeat(10**9,seq(call('x'),call('x'))),lib)
        self.assertEqual(got['M:commands'],2*10**9)
        self.assertEqual(got['M:read'],4*10**9)
        with self.assertRaises(ValueError):counts(call('x'),{'x':call('x')})

    def test_multisite_scratch_checked(self):
        h={'resources':{'portA':1,'portB':1},'sites':{'A':{'words':8},'B':{'words':8}},'nets':{}}
        b={'id':'b','site':'A','ticks':4,'resources':['portA','portB'],'nets':[],
           'scratch_words':8,'scratch_by_site':{'A':8,'B':8},'external_read_words':3,'external_write_words':1}
        t=[{'id':'t','bindings':[b]}];p=search(t,h)
        self.assertEqual(verify(t,h,p)['peak_words'],{'A':8,'B':8})
        h['sites']['B']['words']=7
        with self.assertRaises(ValueError):search(t,h)

    def test_capacity_and_arbitrary_inventory_are_input_driven(self):
        # Unit-only symbolic measurements. Formal model runs use native logs.
        h={'sites':{},'resources':{},'nets':{},'leaf_inventory':{},'virtual_memory':{
            'kind':'pr182-bounded-v1','channels':2,'period':6,'core_period':10,'slots':8,
            'queue':32,'bank_count':4,'bank_interleave_bytes':64,'row_bytes':1024,
            'bank_issue_cycles':2,'word_bytes':16,'credits':4,'phase':1,'latency':20,
            'row_miss_cycles':6,'turnaround_cycles':4,'address_bits':40}}
        for group,macro in [('compute_a','M'),('auxiliary_xyz','E')]:
            site=group+'_private';port=group+'_port';h['sites'][site]={'words':1024}
            h['resources'].update({group+'.'+macro:1,group+'.LC.service':1,port:1})
            for d in ('read','write'):h['nets'][group+'.'+macro+'.'+d]={'cost':1,'fixed':False}
            h['leaf_inventory'][group]={'macros':[macro],'site':site,'io_resource':port,
                'io_read_ticks':3,'io_write_ticks':3,'memory_group':0}
        m={'values':{'a':{'shape':[2]},'b':{'shape':[2]},'c':{'shape':[2]}},
            'tasks':[{'id':'sum','op':'Add','inputs':['a','b'],'outputs':['c']}]}
        primitive={'instructions':[{'id':'v0','kernel':'sum','op':'Add','inputs':['a','b'],
            'shape':[2],'exponent':-12,'bits':32,'attributes':{'signs':[1,1]}}]}
        with patch('streaming_ir.duration',return_value=1):
            for size in (2048,1024,8):
                for s in h['sites'].values():s['words']=size
                ir=compile_graph(m,h,[{'id':'sum','shape':[2],'exponent':-12}],{},primitive)
                plan=search(ir['tasks'],ir['hardware']);self.assertTrue(verify(ir['tasks'],ir['hardware'],plan)['passed'])
            broken=deepcopy(h)
            for s in broken['sites'].values():s['words']=7
            with self.assertRaises(ValueError):compile_graph(m,broken,[{'id':'sum','shape':[2],'exponent':-12}],{},primitive)
            with self.assertRaises(ValueError):compile_graph(m,h,[{'id':'sum','shape':[2],'exponent':-12}],{})
            with patch('verify_primitive_cost.duration',return_value=1):
                ir=compile_graph(m,h,[{'id':'sum','shape':[2],'exponent':-12}],{},primitive)
                self.assertTrue(verify_cost(ir)['passed'])
                ir['tasks'][0]['bindings'][0]['external_write_words']-=1
                with self.assertRaises(ValueError):verify_cost(ir)


if __name__=='__main__':unittest.main()
