import json
from pathlib import Path
import tempfile
import unittest

from flow import run
from loop_dp import search
from test_resource_base import template
from test_router import sample


def inputs():
    hardware={'resources':{'r':1},'sites':{'left.S':{'words':1024}},
              'nets':{'transfer':{'cost':1,'fixed':False}},'leaf_inventory':{
                  n:{'macros':['X'],'words':1024} for n in ('left','right')}}
    tasks=[{'id':'task0','bindings':[{'id':'bound','site':'left.S','resources':['r'],
            'ticks':1,'nets':['transfer'],'scratch_words':1,'external_read_words':0,'external_write_words':0}]}]
    ir={'hardware':hardware,'tasks':tasks};plan=search(tasks,hardware)
    catalog={'schema_version':'route-contract/1','demands':{'transfer':{'signals':[
        {'name':'data','width':1,'driver':'left/out','sinks':['right/in']}],'requires':[]}}}
    return ir,plan,{'variant':template()},{'technology':sample()['technology']},catalog


class FlowTests(unittest.TestCase):
    def test_declared_native_service_emits_no_unnecessary_upper_wire(self):
        ir,plan,library,rules,_=inputs()
        library['variant']['capabilities']['realizations']={
            '{group}.service':{'kind':'native_service','leaf_instances':['leaf']}}
        catalog={'schema_version':'route-contract/1','demands':{
            'transfer':{'realization':{'kind':'native_service','id':'left.service'}}}}
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'new'
            result=run(ir,plan,library,rules,output,catalog=catalog,gap_dbu=20,via_resistance_ohm=.08)
            self.assertEqual(result['status'],'backend_geometry_exported')
            self.assertEqual(result['native_or_external_realizations'],1)
            self.assertEqual(result['routed_nets'],0)
            self.assertIn('NETS 0 ;',(output/'backend/upper.def').read_text())
            self.assertFalse(result['physical_qualified'])

    def test_plan_to_real_backend_format_preserves_binding_users(self):
        ir,plan,library,rules,catalog=inputs()
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'new'
            result=run(ir,plan,library,rules,output,catalog=catalog,gap_dbu=20,via_resistance_ohm=.08)
            self.assertEqual(result['status'],'backend_geometry_exported')
            self.assertEqual(result['routed_nets'],1)
            request=json.loads((output/'requirements.json').read_text())
            self.assertEqual(request['users']['transfer'],[{'task_id':'task0','binding_id':'bound'}])
            self.assertIn('NETS 1 ;',(output/'backend/upper.def').read_text())
            self.assertFalse(result['physical_qualified'])

    def test_missing_contract_is_preserved_not_invented(self):
        ir,plan,library,rules,_=inputs()
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'new'
            result=run(ir,plan,library,rules,output,gap_dbu=20,via_resistance_ohm=.08)
            self.assertEqual(result['status'],'resource_binding_incomplete')
            self.assertEqual(result['diagnostics'][0]['demand_id'],'transfer')
            self.assertFalse((output/'backend').exists())

    def test_search_budget_failure_does_not_export_completed_geometry(self):
        ir,plan,library,rules,catalog=inputs()
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'new'
            result=run(ir,plan,library,rules,output,catalog=catalog,gap_dbu=20,
                       max_expansions=1,via_resistance_ohm=.08)
            self.assertEqual(result['status'],'route_search_incomplete')
            self.assertFalse((output/'backend').exists())
            self.assertTrue(json.loads((output/'routing-feedback.json').read_text())['observations'])


if __name__=='__main__':unittest.main()
