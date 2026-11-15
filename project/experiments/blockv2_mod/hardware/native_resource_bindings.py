"""Enumerate service-to-macro RTL bindings without inferred group wiring.

This is structural binding, not physical pin placement or timing admission.
A service controller must run under the controller that owns its macros.
Multi-owner operations must be decomposed into scheduled service stages.
"""
from itertools import product
import json
from pathlib import Path
from macro_inventory import build_mod
from service_resources import register

def candidates(service, inventory, controller_owners):
    if service.get('diagnostic_only'):return []
    groups=inventory['control_groups']
    if set(controller_owners)-set(groups):
        raise ValueError('unknown control owner')
    result=[]
    adapters=register(inventory)
    for owner in sorted(controller_owners):
        choices=[]
        for req in service['resource_requirements']:
            choices.append([
                inventory['macro_instances'][instance]
                for instance in groups[owner]['macros']
                if (inventory['macro_instances'][instance]['master']==req['required_native_master'] or
                    req['required_native_master'] in inventory['macro_instances'][instance].get('compatible_native_masters',[]))
            ])
        for selected in product(*choices):
            ids=[x['instance'] for x in selected]
            # No implicit alias of simultaneous resource requirements.
            if len(ids)!=len(set(ids)):continue
            controller=owner+'.service.'+service['module']
            edges=[];bindings={};used_adapters=[]
            for req,macro in zip(service['resource_requirements'],selected):
                bindings[req['resource']]=macro['instance']
                for pin in req['ports']:
                    client={'instance':controller,'pin':pin['service_pin'],
                            'kind':'parent_service_controller'}
                    leaf={'instance':macro['instance'],'pin':pin['macro_pin'],
                          'kind':'functional_macro'}
                    adapter=adapters.get(macro['instance']+'.service_selector')
                    segments=[(client,leaf)]
                    if adapter:
                        if service['module'] not in adapter['client_slots']:
                            raise ValueError('service has no predeclared selector slot')
                        slot=adapter['client_slots'][service['module']]
                        aid=macro['instance']+'.service_selector'
                        if aid not in used_adapters:used_adapters.append(aid)
                        apin={'instance':aid,'pin':'client_'+pin['macro_pin'],
                              'array_index':slot,'kind':'parent_standard_cell_adapter'}
                        mpin={'instance':aid,'pin':'macro_'+pin['macro_pin'],
                              'kind':'parent_standard_cell_adapter'}
                        segments=[(client,apin),(mpin,leaf)]
                    for source,target in segments:
                        driver,sink=(source,target) if pin['direction']=='output' else (target,source)
                        edges.append({'driver':driver,'sink':sink,'shape':pin['shape'],
                                      'state':'candidate_rtl_binding',
                                      'physical_binding':None})
            if service['module'] in ('add_s32_service_controller','rope_native_service_controller','rms_apply_native_service_controller'):
                used_adapters.append(owner+'.S.elementwise_selector')
            result.append({
                'control_owner':owner,'controller_instance':controller,
                'service_module':service['module'],'resources':bindings,
                'required_macro_leases':ids,
                'required_registered_adapters':used_adapters,
                'private_sram':groups[owner]['private_sram'],
                'required_connections':edges,
                'connections_already_present':False,
                'scope':'unselected structural option; service dispatch, SRAM access and resource ownership must be admitted before execution',
            })
    return result

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    services=json.loads((root/'hardware/service-controller-contracts.json').read_text())['services']
    inventory=build_mod()
    rows=[]
    for service in services:
        options=candidates(service,inventory,inventory['control_groups'])
        rows.append({'service':service['module'],'candidates':options})
        print(service['module'],[o['control_owner'] for o in options])
    (root/'evidence/architecture-revision-185/service-binding-options.json').write_text(
        json.dumps({'schema':'unselected-macro-bindings/1','services':rows},indent=2)+'\n')
