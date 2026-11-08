"""Instantiate a supplied resource library; no model name or group count policy.

An assembly is a set of transformed source views, not a fictional merged ODB.
Each source's placed leaf instances remain distinct. Translation preserves its
frozen local wiring; source outlines are packing envelopes, not upper obstacles.
"""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'block_synthesis'))
from route_contract import read_base, validate_base

from native_inventory import sha


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def load_library(path):
    path = Path(path).resolve()
    library = json.loads(path.read_text(encoding='utf-8'))
    need(library.get('schema_version') == 'physical-resource-library/1', 'unsupported resource library')
    result = {}
    for key, item in library['templates'].items():
        p = (path.parent / item['inventory']['path']).resolve()
        need(sha(p) == item['inventory']['sha256'], 'inventory hash differs: ' + key)
        inv = json.loads(p.read_text(encoding='utf-8'))
        views = {}
        for kind, ref in item['views'].items():
            p = (path.parent / ref['path']).resolve()
            need(sha(p) == ref['sha256'], 'resource view hash differs: ' + key + '/' + kind)
            views[kind] = {'path': str(p), 'sha256': ref['sha256']}
        need(all(k in views for k in ('odb', 'netlist', 'gds')), 'missing resource views: ' + key)
        result[key] = {'inventory': inv, 'views': views, 'inventory_sha256': item['inventory']['sha256'],
                       'capabilities': item.get('capabilities', {})}
    return result


def place(instances, library, *, gap_dbu, aspect=1.0, alignment_dbu=1):
    """Deterministic shelf placement for native source patches; explicit baseline."""
    need(type(gap_dbu) is int and gap_dbu >= 0, 'invalid placement gap')
    need(math.isfinite(aspect) and aspect > 0, 'invalid aspect')
    need(type(alignment_dbu) is int and alignment_dbu>0, 'invalid placement alignment')
    align=lambda x: ((x+alignment_dbu-1)//alignment_dbu)*alignment_dbu
    sizes = {}
    for instance, template in instances.items():
        need(template in library, 'unknown physical resource: ' + template)
        x0, y0, x1, y1 = library[template]['inventory']['die']
        need(x0 < x1 and y0 < y1, 'invalid source bounds')
        sizes[instance] = (x1-x0, y1-y0)
    need(sizes, 'empty resource inventory')
    target = max(max(w for w,h in sizes.values()),
                 math.ceil(math.sqrt(sum((w+gap_dbu)*(h+gap_dbu) for w,h in sizes.values()) * aspect)))
    x, y, row_height, width = 0, 0, 0, 0
    positions = {}
    for name in sorted(sizes, key=lambda n: (-sizes[n][1], -sizes[n][0], n)):
        w,h = sizes[name]
        if x and x+w > target:
            x, y, row_height = 0, align(y+row_height+gap_dbu), 0
        positions[name] = [x,y]
        width = max(width,x+w)
        x = align(x+w+gap_dbu)
        row_height = max(row_height,h)
    return positions, [0,0,width,y+row_height]


def instances_from_hardware(hardware, library):
    """Bind #220's actual leaf_inventory to library capabilities, not ID prefixes."""
    result = {}
    for name, group in hardware['leaf_inventory'].items():
        explicit = group.get('physical_template')
        candidates = [key for key, entry in library.items()
                      if set(entry.get('capabilities', {}).get('macros', [])) == set(group['macros'])
                      and entry['capabilities'].get('private_s_words', 0) >= group['words']
                      and (explicit is None or key == explicit)]
        need(len(candidates) == 1, 'resource template binding must be unique: ' + name)
        result[name] = candidates[0]
    return result


def assemble(instances, library, positions, bounds):
    need(set(instances) == set(positions), 'placement does not cover resource inventory')
    units = {library[t]['inventory']['dbu_per_micron'] for t in instances.values()}
    need(len(units)==1, 'mixed resource DBU requires an explicit conversion')
    views, assemblies, leaves, endpoints, native = {}, [], [], {}, {}
    envelopes = []
    def shifted(rect, dx, dy):
        return [rect[0]+dx,rect[1]+dy,rect[2]+dx,rect[3]+dy]
    for name, template in sorted(instances.items()):
        need(name and '/' not in name, 'resource instance ID must be unambiguous')
        resource = library[template]; inv = resource['inventory']
        pos = positions[name]
        need(len(pos)==2 and all(type(x) is int for x in pos), 'integer DBU placement required')
        dx,dy = pos[0]-inv['die'][0],pos[1]-inv['die'][1]
        envelope = shifted(inv['die'],dx,dy)
        need(bounds[0]<=envelope[0] and bounds[1]<=envelope[1] and
             envelope[2]<=bounds[2] and envelope[3]<=bounds[3], 'source outside placement bounds')
        for other in envelopes:
            need(envelope[2]<=other[0] or other[2]<=envelope[0] or
                 envelope[3]<=other[1] or other[3]<=envelope[1], 'overlapping native source patches')
        envelopes.append(envelope)
        refs = {}
        for kind,ref in resource['views'].items():
            key=name+':'+kind; views[key]=deepcopy(ref); refs[kind]=key
        assemblies.append({'id':name,'template':template,'translation_dbu':[dx,dy],
                           'source_top':inv['top'],'source_bounds_dbu':inv['die'],
                           'views':refs,'inventory_sha256':resource['inventory_sha256']})
        for leaf in inv['macros']:
            leaves.append({**deepcopy(leaf),'instance':name+'/'+leaf['instance'],
                           'control_group':name,'rect':shifted(leaf['rect'],dx,dy)})
        for term,meta in inv['terms'].items():
            if meta['signal_type']!='SIGNAL':continue
            shapes=[{'layer':'M10','object':name+'/'+term+'/shape/'+str(i),
                     'rect_dbu':shifted(s['rect'],dx,dy)}
                    for i,s in enumerate(meta['shapes']) if s['layer']=='metal10']
            if not shapes:continue
            need(meta['direction'] in ('INPUT','OUTPUT'), 'unsupported bidirectional endpoint')
            component=name+'/'+meta['native_net']
            physical=name+'/'+term
            role='driver' if meta['direction']=='OUTPUT' else 'sink'
            endpoints[physical]={'odb_term':physical,'native_net':component,'role':role,
                                 'm10_shapes':shapes,'source_term':term,'assembly':name}
            if role=='driver':
                need(component not in native or native[component]['driver']==physical,
                     'aliased native outputs require explicit canonical driver metadata')
                native[component]={'driver':physical}
    return {'schema_version':'route-contract/1','base_id':'assembled-resource-candidate',
            'state':'candidate','assembly_state':'placed_source_views',
            'dbu_per_micron':next(iter(units)),'bounds_dbu':bounds,
            'views':views,'assemblies':assemblies,'leaf_instances':leaves,
            'endpoints':endpoints,'fixed_native_nets':native,
            'physical_qualified':False,
            'scope':'translated native resource views; independent leaves retained; not a stitched product ODB'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('resources',type=Path,help='#220 IR/hardware, or instance ID -> physical template ID JSON')
    p.add_argument('library',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--gap-dbu',type=int,required=True);p.add_argument('--aspect',type=float,default=1.0)
    p.add_argument('--alignment-dbu',type=int,default=1)
    a=p.parse_args(); resources=json.loads(a.resources.read_text(encoding='utf-8'))
    library=load_library(a.library)
    hardware=resources.get('hardware', resources)
    instances=instances_from_hardware(hardware,library) if 'leaf_inventory' in hardware else resources
    positions,bounds=place(instances,library,gap_dbu=a.gap_dbu,aspect=a.aspect,alignment_dbu=a.alignment_dbu)
    base=assemble(instances,library,positions,bounds)
    validate_base(base)
    with a.output.open('x',encoding='utf-8') as f:json.dump(base,f,indent=2);f.write('\n')


if __name__=='__main__':main()
