"""Index staged physical source packages into the general resource library."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from native_inventory import sha


def build(inputs, inventories, packages, services=None):
    result={'schema_version':'physical-resource-library/1','templates':{}}
    if services:
        if services.get('schema_version')!='physical-resource-services/1':
            raise ValueError('unsupported supplied service profile')
        if not set(services['templates'])<=set(inputs['resource_capabilities']):
            raise ValueError('service profile contains an unknown resource template')
    for name,capability in inputs['resource_capabilities'].items():
        inventory=Path(inventories)/(name+'-inventory.json')
        package=Path(packages)/name
        inv=json.loads(inventory.read_text(encoding='utf-8'))
        capability=deepcopy(capability)
        if services and name in services['templates']:
            profile=services['templates'][name]
            if profile['inventory_sha256']!=sha(inventory):
                raise ValueError('service profile targets a different native inventory: '+name)
            for field in ('interfaces','realizations'):
                if field in capability:raise ValueError('duplicate capability profile: '+name+'/'+field)
                capability[field]=deepcopy(profile[field])
            capability['service_profile_inventory_sha256']=profile['inventory_sha256']
        views={}
        for kind,filename in [('odb','6_final.odb'),('netlist','6_final.v'),('gds','6_final.gds')]:
            path=package/'native'/filename
            digest=sha(path)
            if digest!=inv['files']['native/'+filename]['sha256']:
                raise ValueError('package no longer matches native inventory: '+name+'/'+kind)
            views[kind]={'path':str(path.resolve()),'sha256':digest}
        result['templates'][name]={'capabilities':capability,
            'inventory':{'path':str(inventory.resolve()),'sha256':sha(inventory)},'views':views}
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','inventories','packages','output'):p.add_argument(name,type=Path)
    p.add_argument('--services',type=Path,help='Explicit hash-bound native service/boundary declarations')
    a=p.parse_args()
    library=build(json.loads(a.inputs.read_text(encoding='utf-8')),a.inventories,a.packages,
                  json.loads(a.services.read_text(encoding='utf-8')) if a.services else None)
    with a.output.open('x',encoding='utf-8') as f:json.dump(library,f,indent=2);f.write('\n')
