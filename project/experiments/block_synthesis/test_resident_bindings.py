from copy import deepcopy
import unittest
from unittest.mock import patch

from resident_bindings import digest,region_choices,uniform_contract,variants_for
from streaming_ir import native_operand_components,templates
from test_dot_cache import example
import test_native_pointwise as pointwise_fixture
from test_resident_timing import timing
from verify_resident_bindings import verify


def fixture():
    program=pointwise_fixture.TestNativePointwise().program();ir=example(words=64);h=ir['hardware']
    for m in h['leaf_inventory'].values():m['words']=64
    q=timing();q['profile']['P'].update({str(80+s):12 for s in range(64)})
    q['profile']['P'].update({str(144+s):12 for s in range(64)});q['profile']['P']['3']=24
    q['profile']['E']['54']=25
    h['tile_service_profiles']={'rtl_sha256':q['rtl_sha256']}
    h['tile_service_bindings']={'kind':'native-tile-instance-services-v1',
        'qualification_sha256':digest(h['tile_service_profiles']),'P':['matrix'],'E':['vector'],
        'evidence':'synthetic unit fixture; no product qualification'}
    ir['primitive_program']=program;ir['model']={'values':dict(program['initial_formats'])}
    ir['primitive_regions']={n['id']:{'address_words':100+3*i,'words':3} for i,n in enumerate(program['instructions'])}
    ir['external_regions']={n:{'address_words':3*i,'words':3} for i,n in enumerate(program['initial_formats'])}
    ir['native_constants']={str(n):{'address_words':1000+i,'words':1} for i,n in enumerate((0,1,65536))}
    ir['required_external_bytes']=20000
    ir['native_operand_components']=native_operand_components(program)
    ir['program']=[{'id':n['id'],'temporary_external_region':{'address_words':200+64*i,'words':64}}
                   for i,n in enumerate(program['instructions'])]
    ir['tasks']=[{'id':n['id'],'bindings':[{'id':'original'}]} for n in program['instructions']]
    with patch('streaming_ir.duration',return_value=1):ir['native_templates']=templates({})
    return ir,q


class TestResidentBindings(unittest.TestCase):
    def test_candidate_transports_cannot_be_promoted_to_qualified_bindings(self):
        ir,q=fixture();variants_for(ir,q,width=4)
        key=next(iter(ir['resident_recipes']));recipe=ir['resident_recipes'].pop(key)
        recipe['plan']['transports']=[{'id':'unqualified'}]
        ir['resident_recipes'][digest(recipe)]=recipe
        with self.assertRaisesRegex(ValueError,'no qualified full-scheduler'):verify(ir,numeric=False)

    def test_actual_source_rules_preserve_old_pool_and_reject_forged_work(self):
        ir,q=fixture();old=deepcopy(ir['tasks']);variants_for(ir,q,width=4)
        self.assertEqual(ir['tasks'],old);self.assertEqual(len(ir['resident_actions']),1)
        self.assertEqual(verify(ir)['synthetic_numeric_cases'],35)
        for field in ('ticks','external_read_words'):
            bad=deepcopy(ir);bad['resident_actions'][0]['bindings'][0][field]-=1
            with self.assertRaisesRegex(ValueError,'work/resources'):verify(bad,numeric=False)
        bad=deepcopy(ir);bad['resident_actions'][0]['bindings'][0]['resident_region']['actor_map']['matrix']='vector'
        with self.assertRaisesRegex(ValueError,'instance'):verify(bad,numeric=False)
        bad=deepcopy(ir);bad['resident_actions'][0]['bindings'][0]['resident_region']['elements']-=1
        with self.assertRaisesRegex(ValueError,'iteration'):verify(bad,numeric=False)

    def test_uniform_loop_rejects_broadcast_alias_and_unmeasured_commands(self):
        ir,q=fixture();names=[n['id'] for n in ir['primitive_program']['instructions']]
        self.assertEqual(uniform_contract(ir,names)['elements'],3)
        for mutate in ('broadcast','view','overlap'):
            bad=deepcopy(ir)
            if mutate=='broadcast':bad['primitive_program']['initial_formats']['x']['shape']=[1,3]
            elif mutate=='view':bad['primitive_program']['initial_formats']['x']['op']='View'
            else:bad['external_regions']['y']['address_words']=bad['external_regions']['x']['address_words']
            with self.assertRaises(ValueError):uniform_contract(bad,names)
        q['profile']['P'].pop('173');variants_for(ir,q)
        self.assertEqual(ir['resident_actions'],[])
        self.assertIn('unmeasured',ir['resident_scope']['rejected'][0]['reason'])
        choices=region_choices(ir['primitive_program'],(2,4))
        self.assertEqual(len(choices),7);self.assertEqual(choices[0],names)


if __name__=='__main__':unittest.main()
