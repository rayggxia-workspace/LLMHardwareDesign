from copy import deepcopy
import unittest
from unittest.mock import patch

from native_pointwise import bind_external,counts,lower as native_lower
from primitive_slice import select
from primitive_stages import lower as stages
from streaming_ir import compile_graph,native_operand_components
from test_dot_cache import example
from test_native_pointwise import node
from verify_primitive_cost import verify,verify_source_closure


def source():
    model={'values':{'x':{'shape':[3]},'out':{'shape':[3]}},
        'tasks':[{'id':'region','op':'Mul','inputs':['x'],'outputs':['out']}], 'outputs':['out']}
    nodes=[node('a','Convert',['x'],shift=0),
           node('c','Constant',[],shape=(),raw=-1),
           node('p','Product',['a','c'],shift=0)]
    for n in nodes:n['kernel']='region' if n['id']=='p' else 'upstream'
    program={'instructions':nodes,'outputs':{'out':'p'},'initial_formats':{'x':{'shape':[3],'bits':32}}}
    return model,program


class TestPrimitiveSlice(unittest.TestCase):
    def test_explicit_boundary_literal_proof_and_original_source_immutable(self):
        m,p=source();before=deepcopy((m,p));sm,sp,scope=select(m,p,['p'],'a'*64)
        self.assertEqual((m,p),before)
        self.assertEqual([n['id'] for n in sp['instructions']],['c','p'])
        self.assertEqual(set(scope['external_boundaries']),{'a'})
        self.assertEqual(sp['initial_formats']['a']['bits'],32)
        self.assertEqual(sp['initial_formats']['a']['boundary_source']['source_sha256'],'a'*64)
        self.assertEqual(sm['values']['a']['shape'],[3])
        self.assertEqual(native_operand_components(sp)['p'],native_operand_components(p)['p'])
        self.assertEqual(native_operand_components(sp)['p'],[3,1])

    def test_closed_cut_compiles_audits_and_resolves_real_reserved_addresses(self):
        m,p=source();sm,sp,_=select(m,p,['p'],'a'*64)
        with patch('streaming_ir.duration',return_value=1):
            ir=stages(compile_graph(sm,example()['hardware'],[{'id':'region','shape':[3],'exponent':0}],{},sp))
        with patch('verify_primitive_cost.duration',return_value=1):self.assertTrue(verify(ir)['passed'])
        graph=bind_external(native_lower(sp,['p'],2),ir)
        for o in graph['objects'].values():self.assertIn('external_address',o)
        self.assertEqual(graph['external_scratch_words'],{'p':3})
        self.assertGreater(counts(graph)['M:commands'],1)
        bad=deepcopy(ir);bad['program'][0]['temporary_external_region']['words']=1
        with self.assertRaisesRegex(ValueError,'scratch'):bind_external(native_lower(sp,['p']),bad)
        bad=deepcopy(ir);bad['required_external_bytes']=0
        with self.assertRaisesRegex(ValueError,'extent'):bind_external(native_lower(sp,['p']),bad)

    def test_unclosed_historical_cut_is_rejected_before_default_width_counting(self):
        m,p=source();p['instructions']=p['instructions'][-1:]
        ir={'model':m,'primitive_program':p}
        with self.assertRaisesRegex(ValueError,'undeclared primitive operand a'):verify_source_closure(ir)
        with self.assertRaisesRegex(ValueError,'undeclared primitive operand a'):verify(ir)
        p['instructions'].insert(0,node('a','Convert',['p'],shift=0))
        with self.assertRaisesRegex(ValueError,'defined before'):verify_source_closure(ir)

    def test_missing_full_source_or_colliding_boundary_never_invented(self):
        m,p=source()
        for names,sha in (([], 'a'*64),(['missing'],'a'*64),(['p'],'unknown')):
            with self.assertRaises(ValueError):select(m,p,names,sha)
        p['instructions'][-1]['inputs'][0]='undefined'
        with self.assertRaisesRegex(ValueError,'undeclared'):select(m,p,['p'],'a'*64)
        m,p=source();m['values']['a']={'shape':[3]}
        with self.assertRaisesRegex(ValueError,'collides'):select(m,p,['p'],'a'*64)


if __name__=='__main__':unittest.main()
