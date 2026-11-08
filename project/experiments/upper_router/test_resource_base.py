import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from resource_base import assemble, instances_from_hardware, place
from adapter import bind_request
from route_contract import VERSION, elaborate, validate_base, verify_requirements


def template():
    return {'views':{k:{'path':'fixture.'+k,'sha256':'a'*64} for k in ('odb','netlist','gds')},
            'inventory_sha256':'b'*64,'capabilities':{'macros':['X'],'private_s_words':1024},
            'inventory':{'top':'fixture','dbu_per_micron':1,'die':[10,20,110,120],
                         'macros':[{'instance':'leaf','master':'real_leaf','orientation':'R0','rect':[20,30,40,50]}],
                         'terms':{name:{'signal_type':'SIGNAL','direction':direction,'native_net':name,
                                        'shapes':[{'layer':'metal10','rect':rect}]}
                                  for name,direction,rect in [('out','OUTPUT',[20,30,30,40]),
                                                              ('in','INPUT',[70,80,80,90])]}}}


class ResourceBaseTests(unittest.TestCase):
    def test_native_and_external_services_do_not_create_fictional_m10_nets(self):
        resource=template()
        resource['capabilities']['realizations']={
            '{group}.compute':{'kind':'native_service','leaf_instances':['leaf']},
            '{group}.load':{'kind':'external_boundary','leaf_instances':['leaf'],'terms':['in','out']}}
        # A real resource boundary may reside below M10. It must retain its
        # physical layer, rather than becoming a fictitious late-routing pin.
        resource['inventory']['terms']['in']['shapes'][0]['layer']='metal3'
        library={'variant':resource};instances={'resource0':'variant'}
        positions,bounds=place(instances,library,gap_dbu=20)
        base=assemble(instances,library,positions,bounds)
        self.assertNotIn('resource0/in',base['endpoints'])
        self.assertEqual(base['realizations']['resource0.load']['boundary_pins']['resource0/in']['shapes'][0]['layer'],'metal3')
        catalog={'schema_version':VERSION,'demands':{
            'compute':{'realization':{'kind':'native_service','id':'resource0.compute'},'requires':['load']},
            'load':{'realization':{'kind':'external_boundary','id':'resource0.load'}}}}
        request=elaborate({'compute':[]},catalog,base,{})
        verify_requirements(request,{'compute':[]},catalog,base,{})
        self.assertEqual(request['status'],'endpoint_binding_complete')
        self.assertEqual(len(request['realizations']),2)
        self.assertEqual(request['members'],[])
        self.assertEqual(request['nets'],[])
        self.assertFalse(request['physical_qualified'])
        bad=copy.deepcopy(base);del bad['realizations']['resource0.load']
        missing=elaborate({'compute':[]},catalog,bad,{})
        self.assertEqual(missing['status'],'unbound')
        self.assertEqual(missing['unresolved'][0]['reason'],'missing_native_realization')
        bad=copy.deepcopy(base);bad['realizations']['resource0.compute']['views']={}
        with self.assertRaisesRegex(ValueError,'another source view'):
            elaborate({'compute':[]},catalog,bad,{})
        bad=copy.deepcopy(base);bad['realizations']['resource0.compute']['leaf_instances']=['invented/leaf']
        with self.assertRaisesRegex(ValueError,'leaf mismatch'):
            elaborate({'compute':[]},catalog,bad,{})
        bad=copy.deepcopy(base);bad['realizations']['resource0.load']['boundary_pins']={}
        with self.assertRaisesRegex(ValueError,'actual boundary pins'):
            elaborate({'compute':[]},catalog,bad,{})
        invalid=copy.deepcopy(catalog);invalid['demands']['load']['signals']=[{'name':'fiction'}]
        with self.assertRaisesRegex(ValueError,'also invent bit nets'):
            elaborate({'compute':[]},invalid,base,{})

    def test_standalone_cli_checks_actual_view_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); inv=root/'inventory.json'
            inv.write_text(json.dumps(template()['inventory']))
            views={}
            for kind in ('odb','netlist','gds'):
                p=root/('view.'+kind);p.write_bytes(b'explicit synthetic fixture')
                views[kind]={'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            library={'schema_version':'physical-resource-library/1','templates':{'variant':{
                'inventory':{'path':inv.name,'sha256':hashlib.sha256(inv.read_bytes()).hexdigest()},
                'views':views,'capabilities':template()['capabilities']}}}
            (root/'library.json').write_text(json.dumps(library))
            (root/'hardware.json').write_text(json.dumps({'leaf_inventory':{
                'left':{'macros':['X'],'words':10},'right':{'macros':['X'],'words':10}}}))
            cmd=[sys.executable,str(Path(__file__).with_name('resource_base.py').resolve()),
                 str(root/'hardware.json'),str(root/'library.json'),str(root/'base.json'),'--gap-dbu','20']
            r=subprocess.run(cmd,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            self.assertEqual(r.returncode,0,r.stdout)
            self.assertEqual(len(json.loads((root/'base.json').read_text())['assemblies']),2)
            (root/'view.odb').write_bytes(b'changed')
            cmd[4]=str(root/'base-rejected.json')
            r=subprocess.run(cmd,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            self.assertNotEqual(r.returncode,0)
            self.assertIn('resource view hash differs',r.stdout)

    def test_resource_count_and_translation_not_names(self):
        library={'variant':template()}; original=copy.deepcopy(library)
        for count in (2,9,11):
            hardware={'leaf_inventory':{f'resource{i}':{'macros':['X'],'words':1024} for i in range(count)}}
            instances=instances_from_hardware(hardware,library)
            positions,bounds=place(instances,library,gap_dbu=20)
            base=assemble(instances,library,positions,bounds);validate_base(base)
            self.assertEqual(len(base['leaf_instances']),count)
            self.assertEqual(len(base['endpoints']),count*2)
            self.assertEqual(len(base['assemblies']),count)
            for leaf in base['leaf_instances']:
                x,y=positions[leaf['control_group']]
                self.assertEqual(leaf['rect'],[x+10,y+10,x+30,y+30])
        self.assertEqual(original,library)

    def test_bound_cross_instance_net_uses_transformed_native_pins(self):
        library={'variant':template()};instances={'first':'variant','second':'variant'}
        positions,bounds=place(instances,library,gap_dbu=20)
        base=assemble(instances,library,positions,bounds)
        catalog={'schema_version':VERSION,'demands':{'transfer':{'signals':[
            {'name':'valid','width':1,'driver':'first/out','sinks':['second/in']}], 'requires':[]}}}
        request=elaborate({'transfer':[]},catalog,base,{})
        self.assertEqual(request['status'],'endpoint_binding_complete')
        spec=bind_request(request,base,{'bounds':bounds})
        self.assertEqual(spec['pins']['second/in'],
                         [base['endpoints']['second/in']['m10_shapes'][0]['rect_dbu']])
        self.assertEqual(len(spec['nets']),1)

    def test_invalid_or_ambiguous_resource_inputs_rejected(self):
        library={'variant':template()};instances={'a':'variant','b':'variant'}
        with self.assertRaisesRegex(ValueError,'overlapping'):
            assemble(instances,library,{'a':[0,0],'b':[1,1]},[0,0,200,200])
        with self.assertRaisesRegex(ValueError,'outside'):
            assemble({'a':'variant'},library,{'a':[-1,0]},[0,0,200,200])
        with self.assertRaisesRegex(ValueError,'unique'):
            instances_from_hardware({'leaf_inventory':{'a':{'macros':['X'],'words':1025}}},library)
        with self.assertRaisesRegex(ValueError,'unique'):
            instances_from_hardware({'leaf_inventory':{'a':{'macros':['X'],'words':1}}},
                                    {**library,'other':template()})
        broken=copy.deepcopy(library);broken['variant']['inventory']['dbu_per_micron']=2
        mixed={**library, 'other':broken['variant']}
        with self.assertRaisesRegex(ValueError,'mixed'):
            assemble({'a':'variant','b':'other'},mixed,{'a':[0,0],'b':[200,0]},[0,0,500,500])


if __name__=='__main__':unittest.main()
