"""Independent OpenDB rectangle -> GDS readback, upper rules and native XOR.

Run under KLayout, with ROUTER_HANDOFF / ROUTER_NATIVE_GDS set explicitly.
Consumes actual OpenDB dump, rather than generating GDS from the router result.
No electrical/timing qualification is inferred from these geometric checks.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import pya


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda:f.read(8 << 20),b''):h.update(data)
    return h.hexdigest()

run=Path(os.environ['ROUTER_HANDOFF'])
native_file=Path(os.environ['ROUTER_NATIVE_GDS'])
data=json.loads((run/'bindings.json').read_text())
if sha(native_file)!=data['context']['native_gds_sha256']:
    raise ValueError('native GDS fingerprint mismatch')
scale=data['dbu_per_micron']
layers={'M11':(211,0),'M12':(213,0),'V10':(210,0),'V11':(212,0)}
names={'metal11':'M11','metal12':'M12','via10':'V10','via11':'V11'}
aliases={};actual={n:[] for n in data['nets']}
for row in (run/'odb-geometry.tsv').read_text().splitlines():
    if row.startswith('# NET '):
        _,_,alias,name=row.split()
        aliases[alias]=bytes.fromhex(name).decode()
    elif row and not row.startswith('#'):
        net,layer,kind,*coords=row.split('\t')
        if layer in names:
            name=aliases[net]
            if name not in actual:raise ValueError('foreign net in OpenDB')
            actual[name].append((names[layer],list(map(int,coords))))

def region(rows,layer):
    r=pya.Region()
    for l,b in rows:
        if l==layer:r.insert(pya.Box(*b))
    return r.merged()

for name,expected in data['expected_shapes'].items():
    for layer in layers:
        if not (region(expected,layer)^region(actual[name],layer)).is_empty():
            raise ValueError('DEF/OpenDB geometry differs: '+name+'/'+layer)

layout=pya.Layout();layout.dbu=1/scale;top=layout.create_cell('GENERIC_UPPER_INTERCONNECT')
for name,rows in actual.items():
    for layer,box in rows:
        top.shapes(layout.layer(*layers[layer])).insert(pya.Box(*box)).set_property(1,name)
upper=run/'upper.gds';layout.write(str(upper))
read=pya.Layout();read.read(str(upper))
if not math.isclose(read.dbu,1/scale,rel_tol=0,abs_tol=1e-12):raise ValueError('GDS grid changed')
observed={n:[] for n in data['nets']}
for layer,pair in layers.items():
    index=read.find_layer(*pair)
    if index is None:continue
    for shape in read.top_cell().shapes(index).each():
        if not shape.is_box() or shape.property(1) not in observed:raise ValueError('foreign GDS shape')
        b=shape.box;observed[shape.property(1)].append((layer,[b.left,b.bottom,b.right,b.top]))
for n in actual:
    for l in layers:
        if not (region(actual[n],l)^region(observed[n],l)).is_empty():raise ValueError('GDS roundtrip changed geometry')

allrows=[s for rows in observed.values() for s in rows]
regions={l:region(allrows,l) for l in layers}
t=data['technology']
for l in ('M11','M12'):
    if not regions[l].width_check(t['width']).is_empty():raise ValueError('upper minimum width')
    if not regions[l].space_check(t['spacing']).is_empty():raise ValueError('upper minimum spacing')
for l,v in [('V10','via10'),('V11','via11')]:
    if not regions[l].space_check(t[v]['spacing']).is_empty():raise ValueError('upper cut spacing')
for n,rows in observed.items():
    own={l:region(rows,l) for l in layers}
    for cut,metal in [('V10','M11'),('V11','M11'),('V11','M12')]:
        enc=t['via10' if cut=='V10' else 'via11']['upper_enclosure' if metal=='M12' or cut=='V10' else 'lower_enclosure']
        if not (own[cut].sized(enc)-own[metal]).is_empty():raise ValueError('missing via enclosure')
    for other,orows in observed.items():
        if other>=n:continue
        for l in ('M11','M12'):
            if not (own[l]&region(orows,l)).is_empty():raise ValueError('cross-net metal short')

native=pya.Layout();native.read(str(native_file))
conversion=native.dbu*scale
# Native GDS and ODB are allowed to use different exact integer grids. Reject
# a route that would actually round during composition; do not round it to fit.
for rows in observed.values():
    for layer,coords in rows:
        if any(not math.isclose(x/conversion,round(x/conversion),abs_tol=1e-8) for x in coords):
            raise ValueError('route not representable on native GDS grid')
native_top=native.top_cell()
m10index=native.find_layer(29,0)
if m10index is None:raise ValueError('native M10 absent')
m10=pya.Region(native_top.begin_shapes_rec(m10index)).transformed(pya.ICplxTrans(conversion,0,False,0,0)).merged()
if not (regions['V10'].sized(t['via10']['lower_enclosure'])-m10).is_empty():
    raise ValueError('via10 not fully covered by real native M10')
before={str(info):pya.Region(native_top.begin_shapes_rec(native.find_layer(info))).merged()
        for info in native.layer_infos()}
if any(pair in [(i.layer,i.datatype) for i in native.layer_infos()] for pair in layers.values()):
    raise ValueError('native file already has custom layers')
native.read(str(upper))
native_top.insert(pya.CellInstArray(native.cell('GENERIC_UPPER_INTERCONNECT').cell_index(),pya.Trans()))
combined=run/'combined.gds';native.write(str(combined))
joined=pya.Layout();joined.read(str(combined));joined_top=joined.top_cell()
for layer,pair in layers.items():
    index=joined.find_layer(*pair)
    after=pya.Region() if index is None else pya.Region(joined_top.begin_shapes_rec(index)).transformed(
        pya.ICplxTrans(joined.dbu*scale,0,False,0,0)).merged()
    if not (regions[layer]^after).is_empty():raise ValueError('combined GDS upper geometry changed')
for label,before_region in before.items():
    candidates=[i for i in joined.layer_infos() if str(i)==label]
    if len(candidates)!=1:raise ValueError('native layer disappeared')
    after=pya.Region(joined_top.begin_shapes_rec(joined.find_layer(candidates[0]))).merged()
    if not (before_region^after).is_empty():raise ValueError('native geometry changed: '+label)
report={'schema_version':'upper-physical-readback/1','geometry_passed':True,'native_geometry_xor_zero':True,
        'net_count':len(actual),'sha256':{p.name:sha(p) for p in [run/'upper.def',run/'upper.odb',upper,combined,native_file]},
        'physical_qualified':False,'electrical':'not_evaluated','timing':'not_evaluated',
        'scope':'actual OpenDB/GDS roundtrip; research upper width/spacing/cuts/enclosure; full native shape XOR'}
(run/'physical-readback.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
