"""Extract a router qualification case from accepted, real late-link contracts.

This is a backend interface regression, NOT the complete #220 product mapping.
The router itself has no knowledge of the names/types in these input files.
"""
import argparse
import json
from pathlib import Path
from native_inventory import sha


def make(package, inventory, stack):
    package = Path(package)
    inventory_file = Path(inventory)
    inv = json.loads(inventory_file.read_text())
    stack_file=Path(stack); tech=json.loads(stack_file.read_text())
    pair_file=package/'physical/cut-links.json'
    if pair_file.exists():
        pairs=json.loads(pair_file.read_text())['links']
    else:
        pair_file=package/'upper/overlay.json'
        pairs=[(r['driver'],r['sink']) for r in json.loads(pair_file.read_text())['routes'].values()]
    d=inv['dbu_per_micron'];g=tech['geometry_um']
    def integer(x):
        n=round(x*d)
        if abs(n-x*d)>1e-7:raise ValueError('rule off database grid')
        return n
    v={'cut':integer(g['cut_width']),'lower_enclosure':integer(g['enclosure']),
       'upper_enclosure':integer(g['enclosure']),'spacing':integer(g['cut_spacing'])}
    spec={'schema_version':'upper-router/1','units':'dbu',
          'technology':{'bounds':inv['die'],'origin':[integer(g['track_offset_x']),integer(g['track_offset_y'])],
                        'pitch':integer(tech['placement_start']['regular_via_center_pitch_um']),
                        'width':integer(g['width']),'spacing':integer(g['spacing']),
                        'via10':dict(v),'via11':dict(v)},'pins':{},'nets':[],
          'context':{'native_odb_sha256':inv['files']['native/6_final.odb']['sha256'],
                     'native_gds_sha256':inv['files']['native/6_final.gds']['sha256'],
                     'inventory_sha256':sha(inventory_file),'pair_contract_sha256':sha(pair_file),
                     'stack_sha256':sha(stack_file),'dbu_per_micron':d,
                     'scope':'independent native late-interface regression; not full #220 or nine-group product'}}
    for i,(source,sink) in enumerate(pairs):
        a,b=inv['terms'][source],inv['terms'][sink]
        if a['direction']!='OUTPUT' or b['direction']!='INPUT' or a['native_net']==b['native_net']:
            raise ValueError('invalid native boundary')
        if len(a['drivers'])!=1 or b['drivers'] or not b['sinks']:
            raise ValueError('unqualified native driver/receiver identity')
        for pin in (source,sink):
            spec['pins'][pin]=[s['rect'] for s in inv['terms'][pin]['shapes'] if s['layer']=='metal10']
            if not spec['pins'][pin]:raise ValueError('real M10 landing missing: '+pin)
        spec['nets'].append({'id':'link%06d'%i,'driver':source,'sinks':[sink]})
    return spec


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('package','inventory','stack','output'):p.add_argument(n,type=Path)
    a=p.parse_args();a.output.write_text(json.dumps(make(a.package,a.inventory,a.stack),indent=2)+'\n')
