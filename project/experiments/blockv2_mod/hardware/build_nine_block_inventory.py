"""Expand the five existing block families to the original nine-instance base.

The service dispatch overlay is deliberately separate from the instance inventory.
A registered route is evidence of one service, not the definition of a whole base.
"""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

NAMES = ('P0','P1','P2','C0','U0','J0','F0','U1','J1')

def rename(value, old, new):
    if isinstance(value, str):
        return new + value[len(old):] if value == old or value.startswith(old+'.') else value
    if isinstance(value, list): return [rename(v,old,new) for v in value]
    if isinstance(value, dict): return {rename(k,old,new):rename(v,old,new) for k,v in value.items()}
    return value

def build(template, layout, routes):
    if set(layout['positions_um']) != set(NAMES):
        raise ValueError('layout does not describe the original nine instances')
    result=deepcopy(template)
    result['architecture_accepted']=False
    result['diagnostic_only']=True
    result['architecture_rejection']='Legacy group-as-leaf model and wrapper dispatch; superseded by macro_inventory.py under PR185.'
    result['leaf_inventory']={}
    result['sites']={}
    result['resources']={}
    result['nets']={}
    result['control_groups']={}
    declared={r['group']:r for r in routes['targets']}
    for group in NAMES:
        prototype=group[0]+'0'
        meta=rename(deepcopy(template['leaf_inventory'][prototype]),prototype,group)
        # Separate SRAM address spaces; not RTL target identifiers.
        meta['memory_group']=NAMES.index(group)
        result['leaf_inventory'][group]=meta
        result['sites'][meta['site']]=rename(deepcopy(template['sites'][prototype+'.S']),prototype,group)
        result['sites'][meta['site']]['memory_group']=meta['memory_group']
        for section in ('resources','nets'):
            for name,value in template[section].items():
                if name.startswith(prototype+'.'):
                    result[section][rename(name,prototype,group)]=rename(deepcopy(value),prototype,group)
        control={'site':meta['site']}
        if group in declared: control['block_id']=declared[group]['id']
        result['control_groups'][group]=control
    result['topology_id']=routes['topology_id']
    result['schema']='blockv2-mod-nine-resource-inventory/1'
    result['instance_order']=list(NAMES)
    result['dispatch_inventory_scope']='partial service-route overlay; not the complete instance inventory'
    result['placement_reference']={'positions_um':layout['positions_um'],'scope':'original layout reference, not mod physical implementation'}
    result['native_dispatch_overlay']=routes
    result['scope']='Historical diagnostic resource model; not the corrected blockv2-mod hardware inventory.'
    return result

if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ('template','layout','routes','output'):cli.add_argument(name,type=Path)
    cli.add_argument('--qualification',type=Path,required=True)
    args=cli.parse_args()
    inputs={k:getattr(args,k) for k in ('template','layout','routes')}
    value=build(*(json.loads(p.read_text()) for p in inputs.values()))
    import re
    profiles=[]
    logs=[]
    for index in range(3):
        path=args.qualification / ('native-'+str(index)+'.log')
        text=path.read_text()
        if text.count('NATIVE_LEAF_PROBE_PASS seed=219')!=1:
            raise ValueError('unqualified timing source')
        measurements={}
        for line in text.splitlines():
            if not line.startswith('LEAF '):continue
            fields=dict(re.findall(r'(\w+)=([\w-]+)',line))
            kind=fields.pop('kind')
            ticks=int(fields.pop('ticks',fields.pop('execute_ticks','0')))
            key=kind+':'+json.dumps({k:int(v) for k,v in fields.items()},sort_keys=True,separators=(',',':'))
            if ticks<=0 or key in measurements and measurements[key]!=ticks:
                raise ValueError('inconsistent timing')
            measurements[key]=ticks
        profiles.append(measurements)
        logs.append({'path':str(path.resolve()),'sha256':sha256(path.read_bytes()).hexdigest()})
    if not profiles[0] or profiles[0]!=profiles[1] or profiles[0]!=profiles[2]:
        raise ValueError('timing profiles differ')
    value['native_leaf_profiles']={'measurements':profiles[0],'logs_sha256':[r['sha256'] for r in logs],
        'scope':'serialized native leaf driver; primitive numeric checks, not full LC/S integration'}
    value['timing_source_files']=logs
    value['source_files']={k:{'path':str(p.resolve()),'sha256':sha256(p.read_bytes()).hexdigest()} for k,p in inputs.items()}
    args.output.write_text(json.dumps(value,indent=2)+'\n')
    print('Nine instances:',', '.join(value['instance_order']))
