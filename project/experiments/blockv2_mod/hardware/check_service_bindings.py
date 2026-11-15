"""Check structural options against independent PR185 ownership and RTL ports."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from macro_inventory import build_mod
from native_resource_bindings import candidates
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/architecture-revision-185'

def check():
    inventory=build_mod()
    services=json.loads((ROOT/'hardware/service-controller-contracts.json').read_text())['services']
    expected={
        'add_s32_service_controller':{'C0','F0','J0','J1'},
        'rope_s32_service_controller':{'C0','F0','J0','J1'},
        'rope_native_service_controller':{'C0','F0','J0','J1'},
        'rms_apply_s32_service_controller':{'C0','F0','J0','J1'},
        'rms_apply_native_service_controller':{'C0','F0','J0','J1'},
        'gated_s32_service_controller':{'P0','P1','P2'},
        'rms_s32_service_controller':set(),
        'n32_service_controller':{'U0','U1'},
        'e32_dot_service_controller':{'C0','F0','J0','J1'},
        'projection_local_service_controller':{'P0','P1','P2'},
    }
    rows=[]
    for service in services:
        options=candidates(service,inventory,inventory['control_groups'])
        assert {o['control_owner'] for o in options}==expected[service['module']]
        for option in options:
            for edge in option['required_connections']:
                for ep in (edge['driver'],edge['sink']):
                    kind=ep['kind'];name=ep['instance']
                    assert name not in inventory['control_groups'],'opaque group endpoint'
                    if kind=='functional_macro':assert name in inventory['macro_instances']
                    elif kind=='parent_standard_cell_adapter':
                        assert name in inventory['adapter_instances']
                        if 'array_index' in ep:
                            assert ep['array_index']<inventory['adapter_instances'][name]['parameters']['CLIENTS']
                    elif kind=='parent_service_controller':assert name==option['controller_instance']
                    else:raise AssertionError(kind)
            assert not option['connections_already_present']
            rows.append({'service':service['module'],'owner':option['control_owner'],
                         'macros':list(option['resources'].values()),
                         'adapters':option['required_registered_adapters']})
    # A valid group name cannot be used as an invented macro resource.
    altered=build_mod()
    for instance in altered['control_groups']['C0']['macros']:
        if altered['macro_instances'][instance]['master'] in ('e_s32_ap64','e_s32_mac_ap64'):
            altered['macro_instances'][instance]['master']='removed_for_negative_check'
            altered['macro_instances'][instance].pop('compatible_native_masters',None)
    add=next(s for s in services if s['module']=='add_s32_service_controller')
    assert not candidates(add,altered,['C0'])
    assert not candidates(add,inventory,['U0','U1'])
    receipt={'passed':True,'options':rows,'negative_missing_macro':True,
             'negative_wrong_control_owner':True,
             'scope':'structural options, not service dispatch or whole graph execution'}
    (OUT/'binding-structure-check.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(len(rows),'structural options; negative missing/wrong-owner checks pass')

if __name__=='__main__':check()
