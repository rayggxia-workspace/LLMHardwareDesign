"""Instantiate supplied bit-level native-link contracts on an assembled base.

This is resource-library qualification; it does not invent connections for
missing #220 service definitions. Link lists and instance inventory are data.
"""
import json
from pathlib import Path
from check import digest
from native_inventory import sha
from fixture_case import make


def make_assembly(base,library,packages,stack,native_gds):
    cases={};pins={};nets=[];contracts={}
    for assembly in base['assemblies']:
        template=assembly['template'];name=assembly['id'];resource=library[template]
        if template not in cases:
            # make() reads actual source GDS/ODB and explicit accepted link list.
            # Dataset runner supplies immutable inventory references separately.
            inventory=Path(resource['inventory_path'])
            cases[template]=make(Path(packages)/template,inventory,stack)
        case=cases[template];dx,dy=assembly['translation_dbu']
        for p,rects in case['pins'].items():
            endpoint=name+'/'+p
            assert endpoint in base['endpoints'],'link contract is not an actual resource endpoint'
            pins[endpoint]=[[r[0]+dx,r[1]+dy,r[2]+dx,r[3]+dy] for r in rects]
            assert pins[endpoint]==[s['rect_dbu'] for s in base['endpoints'][endpoint]['m10_shapes']]
        for net in case['nets']:
            nets.append({'id':name+'/'+net['id'],'driver':name+'/'+net['driver'],
                         'sinks':[name+'/'+p for p in net['sinks']]})
        contracts[name]=case['context']
    technology=dict(next(iter(cases.values()))['technology'],bounds=base['bounds_dbu'])
    return {'schema_version':'upper-router/1','units':'dbu','technology':technology,
            'pins':pins,'nets':nets,'context':{'dbu_per_micron':base['dbu_per_micron'],
            'base_sha256':digest(base),'native_gds_sha256':sha(native_gds),
            'source_contracts':contracts,'scope':'complete instantiated resource-library native links; not whole-model functional qualification'}}
