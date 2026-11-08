"""Index staged physical source packages into the general resource library."""
import argparse
import json
from pathlib import Path
from native_inventory import sha


def build(inputs, inventories, packages):
    result={'schema_version':'physical-resource-library/1','templates':{}}
    for name,capability in inputs['resource_capabilities'].items():
        inventory=Path(inventories)/(name+'-inventory.json')
        package=Path(packages)/name
        inv=json.loads(inventory.read_text(encoding='utf-8'))
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
    a=p.parse_args()
    library=build(json.loads(a.inputs.read_text(encoding='utf-8')),a.inventories,a.packages)
    with a.output.open('x',encoding='utf-8') as f:json.dump(library,f,indent=2);f.write('\n')
