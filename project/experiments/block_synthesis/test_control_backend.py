"""Control backend rejection/ABI planning tests. Timings here are unit-only."""
from copy import deepcopy
import json
import unittest
from control_backend import compile_control


def fixture():
    f={'bits':16,'exponent':0,'lanes':8}
    m={'inputs':['x','y','z'],'outputs':['out'],
       'values':{n:{'dtype':'INT16','shape':[8],'format':f.copy()} for n in ('x','y','z','sum','out')},
       'tasks':[{'id':'sum','op':'Add','domain':'llmhardware.native','inputs':['x','y'],'outputs':['sum']},
                {'id':'product','op':'Mul','domain':'llmhardware.native','inputs':['sum','z'],'outputs':['out']}]}
    h={'sites':{'left.S':{'words':1024},'right.S':{'words':1024}},'nets':{},'resources':{},
       'control_groups':{g:{'block_id':i,'site':g+'.S','s_io_ticks':3} for i,g in enumerate(('left','right'))},
       'initial_placement':{'x':'left','y':'left','z':'right'},
       'placement_constraints':{'sum':'left','product':'right'},'output_placement':{'out':'left'},
       'verification_echo':True,'topology_id':123,'abi_id':321}
    for group in h['control_groups']:
        h['resources'].update({group+'.E':1,group+'.LC':1,group+'.S.IO':1})
        for direction in ('read','write'):h['nets'][group+'.E.'+direction]={'cost':1,'fixed':True}
    for n in ('left->right','right->left'):h['nets'][n]={'cost':1}
    cap={'local_words':1024,'record':f,'native_opcodes':{'COMMAND':256,'SEND':257,'RECEIVE':258,'RESERVE':259},
         'operations':{'Add':{'e_op':0,'shift':0},'Mul':{'e_op':2,'shift':0}},
         'max_execution_descriptors':32,'max_instructions':256}
    p={'measurements':{'E:'+json.dumps({'op':op,'shift':0},sort_keys=True,separators=(',',':')):1 for op in (0,2)}}
    return m,h,cap,p


class ControlTests(unittest.TestCase):
    def test_two_renamed_targets_emit_real_descriptor_fields_and_same_nets(self):
        m,h,cap,p=fixture();r=compile_control(m,h,cap,p)
        self.assertEqual(r['plan']['status'],'planned')
        self.assertEqual([x['reason'] for x in r['moves']],['operand','output','verification_export'])
        for group,rows in r['program'].items():
            command=next(x for x in rows if x['native_op']==256)
            self.assertEqual((command['native0']>>2)&3,2)
            self.assertTrue(command['native0']&16)
            self.assertEqual(command['native2'],0 if group=='left' else 2)
        self.assertEqual(len(r['preconnected_demands']),4)
        self.assertEqual({x['id'] for x in r['connections']},{'left->right','right->left'})

    def test_static_conflicting_control_topology_is_not_emitted(self):
        m,h,cap,p=fixture();h['incompatible_nets']=[['left->right','right->left']]
        with self.assertRaisesRegex(ValueError,'no legal static'):compile_control(m,h,cap,p)

    def test_unknown_control_ops_do_not_get_software_fallback(self):
        m,h,cap,p=fixture();m['tasks'][1]['op']='RMSNorm'
        with self.assertRaisesRegex(ValueError,'qualified control subset'):compile_control(m,h,cap,p)

    def test_float_and_wrong_record_format_are_rejected(self):
        for field,value in [('dtype','FLOAT'),('shape',[16]),('format',{'bits':32,'exponent':0,'lanes':4})]:
            m,h,cap,p=fixture();m['values']['x'][field]=value
            with self.assertRaisesRegex(ValueError,'control record'):compile_control(m,h,cap,p)

    def test_standard_onnx_add_is_not_relabelled_saturating(self):
        m,h,cap,p=fixture();m['tasks'][0]['domain']=''
        with self.assertRaisesRegex(ValueError,'qualified control subset'):compile_control(m,h,cap,p)

    def test_limits_are_enforced_before_assembly(self):
        m,h,cap,p=fixture();cap['max_execution_descriptors']=1
        with self.assertRaisesRegex(ValueError,'controller limits'):compile_control(m,h,cap,p)
        m,h,cap,p=fixture();h['control_groups']['right']['block_id']=0
        with self.assertRaisesRegex(ValueError,'distinct local IDs'):compile_control(m,h,cap,p)

    def test_capacity_and_missing_connection_fail_closed(self):
        m,h,cap,p=fixture();h['sites']['right.S']['words']=2048
        with self.assertRaisesRegex(ValueError,'capacity differs'):compile_control(m,h,cap,p)
        m,h,cap,p=fixture();h['nets'].pop('right->left')
        with self.assertRaisesRegex(ValueError,'unregistered control connection'):compile_control(m,h,cap,p)


if __name__=='__main__':unittest.main()
