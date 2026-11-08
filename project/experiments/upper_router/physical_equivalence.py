"""KLayout: independently compare flat ODB against all actual source ODBs.

Includes every placed standard cell/leaf, every native net's metal/pin union,
and every upper net's owners and actual rectangles. Source GDS internals have
their separate unchanged-native XOR gate. OBS never become metal here.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import pya
sys.path.insert(0,str(Path(__file__).resolve().parent))
from native_inventory import sha


root=Path(os.environ['ROUTER_FLAT_OUT'])
cache=Path(os.environ.get('ROUTER_EQUIVALENCE_CACHE',str(root)))
receipt_root=Path(os.environ.get('ROUTER_EQUIVALENCE_RECEIPT',str(root)))
proof=json.loads((root/'source-proof.json').read_text());base=proof['base']
binding=json.loads(Path(os.environ['ROUTER_FLAT_BINDING']).read_text())


def records(path):
    name=None;regions={}
    with path.open() as f:
        for line in f:
            if line.startswith('# NET '):
                if name is not None:yield name,regions
                name=bytes.fromhex(line.split()[3]).decode();regions={}
            elif line and not line.startswith('#'):
                _,layer,kind,*coordinates=line.rstrip().split('\t')
                assert name is not None
                regions.setdefault(layer,pya.Region()).insert(pya.Box(*map(int,coordinates)))
    if name is not None:yield name,regions


def unpack(serialized):
    r=pya.Region()
    for s in serialized:r.insert(pya.Polygon.from_s(s))
    return r


def equal(a,b,net,layer):
    difference=a^b
    if not difference.is_empty():
        failure={'kind':'actual_odb_geometry_differs','net':net,'layer':layer,
                 'difference_bbox':str(difference.bbox()),'difference_area_dbu2':difference.area()}
        (root/'first-failure.json').write_text(json.dumps(failure,indent=2)+'\n')
        raise ValueError(str(failure))


caches={};source_instances={}
for template in sorted({a['template'] for a in base['assemblies']}):
    database=sqlite3.connect(str(cache/('source-'+template+'.sqlite')))
    database.execute('CREATE TABLE polygons (net TEXT PRIMARY KEY, layers TEXT NOT NULL)')
    database.execute('PRAGMA synchronous=OFF');database.execute('BEGIN')
    total=0
    for name,regions in records(root/('source-'+template+'-geometry.tsv')):
        shapes={layer:sorted(p.to_s() for p in r.each_merged()) for layer,r in regions.items()}
        if any(shapes.values()):
            database.execute('INSERT INTO polygons VALUES (?,?)',(name,json.dumps(shapes,separators=(',',':'))));total+=1
    database.commit();caches[template]=database
    entries={}
    for line in (root/('source-'+template+'-instances.tsv')).read_text().splitlines():
        name,master,x,y,orientation=line.split('\t');assert name not in entries
        entries[name]=(master,int(x),int(y),orientation)
    source_instances[template]=entries
    print('SOURCE_CACHE',template,total,len(entries),flush=True)

expected_instances={};assemblies={a['id']:a for a in base['assemblies']};expected_nets=set()
for group,a in assemblies.items():
    dx,dy=a['translation_dbu'];template=a['template']
    for name,(master,x,y,orientation) in source_instances[template].items():
        expected_instances[group+'/'+name]=('SRC_'+template+'_'+master,x+dx,y+dy,orientation)
    expected_nets.update(group+'/'+row[0] for row in caches[template].execute('SELECT net FROM polygons'))
actual_instances={}
for line in (root/'actual-instances.tsv').read_text().splitlines():
    name,master,x,y,orientation=line.split('\t');assert name not in actual_instances
    actual_instances[name]=(master,int(x),int(y),orientation)
assert actual_instances==expected_instances,'actual placed cells differ from immutable native ODBs'
expected_owners=set((root/'expected-owners.tsv').read_text().splitlines())
actual_owners=set((root/'actual-owners.tsv').read_text().splitlines())
assert actual_owners==expected_owners,'actual upper-net ITerm owners differ from source ODBs'
joined=proof['definition']['joined_native_components']
assert set(joined)<=expected_nets
expected_nets-=set(joined);expected_nets.update(joined.values())
upper_layers={'M11':'metal11','M12':'metal12','V10':'via10','V11':'via11'}
all_upper=set(upper_layers.values());seen=set();checked=0


def source_regions(component):
    group,name=component.split('/',1);a=assemblies[group]
    row=caches[a['template']].execute('SELECT layers FROM polygons WHERE net=?',(name,)).fetchone();assert row is not None
    transform=pya.Trans(*a['translation_dbu'])
    return {layer:unpack(polys).transformed(transform) for layer,polys in json.loads(row[0]).items()}


for name,actual in records(root/'actual-geometry.tsv'):
    if not any(not r.is_empty() for r in actual.values()):continue
    assert name in expected_nets and name not in seen,('unexpected/duplicated actual physical net',name)
    seen.add(name);expected={}
    if name.startswith('UPPER_'):
        net=name[len('UPPER_'):];row=binding['nets'][net]
        components={base['endpoints'][p]['native_net'] for p in [row['driver']]+row['sinks']}
        for component in components:
            for layer,r in source_regions(component).items():
                if layer not in expected:expected[layer]=pya.Region()
                expected[layer]+=r
        for layer,box in binding['expected_shapes'][net]:
            expected.setdefault(upper_layers[layer],pya.Region()).insert(pya.Box(*box))
    else:expected=source_regions(name)
    for layer in set(actual)|set(expected):
        equal(actual.get(layer,pya.Region()),expected.get(layer,pya.Region()),name,layer)
    checked+=1
    if checked%25000==0:print('NETS_COMPARED',checked,flush=True)
assert seen==expected_nets,('missing physical nets',len(expected_nets-seen))
result={'passed':True,'native_placed_instances':len(actual_instances),'physical_nets_compared':checked,
        'upper_nets_compared':len(binding['nets']),'upper_iterm_owners':len(actual_owners),
        'all_native_metal_and_pin_unions_xor_zero':True,'all_upper_geometry_xor_zero':True,
        'actual_component_placements_and_models_equal':True,'source_odb_readback_reference':True,
        'scope':'flat actual ODB compared against independently decoded source ODBs and upper route; RC/STA and full GDS DRC are separate gates'}
result['artifact_sha256']={p.name:sha(p) for p in [root/'assembled.odb',root/'assembled.v',
    root/'source-proof.json',root/'actual-geometry.tsv',root/'actual-instances.tsv',root/'actual-owners.tsv']}
result['binding_sha256']=sha(os.environ['ROUTER_FLAT_BINDING'])
(receipt_root/'physical-equivalence.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
