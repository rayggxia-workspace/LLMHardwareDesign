"""Candidate-bound native marker classification; never full-deck acceptance.

Run under allocated klayout -b -r check.py with C_NATIVE_SPEC=/absolute/spec.json.
Spec: output, candidate_id, inputs={gds,def,native,layers,vias,parser},
each input={path,sha256}; evidence={native_origin,metadata_origin} same form.
Origin receipts must bind the actual candidate ODB/DEF/report and metadata export.
"""
import ast, collections, hashlib, json, os, re
from pathlib import Path
import pya

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec_path = Path(os.environ['C_NATIVE_SPEC']).resolve()
spec = json.loads(spec_path.read_text(encoding='utf-8-sig'))
assert set(spec['inputs']) == {'gds','def','native','layers','vias','parser'}
assert set(spec['evidence']) == {'native_origin','metadata_origin'}
bound = dict(spec['inputs'], **spec['evidence'])
for name, item in bound.items():
    assert Path(item['path']).is_absolute(), name
    assert sha(item['path']) == item['sha256'], ('Input hash mismatch',name)
files = {k: Path(v['path']) for k,v in bound.items()}
out = Path(spec['output']); out.mkdir(parents=True, exist_ok=False)
initial = {str(p):sha(p) for p in [spec_path,Path(__file__).resolve(),*files.values()]}
(out/'inputs-before.json').write_text(json.dumps(initial,indent=2))
native_text = files['native'].read_text()
pattern = re.compile(r'violation type: ([^\n]*)\n\s*srcs: ([^\n]*)\n\s*bbox = ([^\n]*?) on Layer (\S+)')
matches = list(pattern.finditer(native_text))
assert len(matches) == len(re.findall(r'violation type:',native_text)), 'Unparsed native marker'
layout = pya.Layout(); layout.read(str(files['gds']))
assert len(list(layout.top_cells())) == 1
top = layout.top_cell(); assert layout.dbu == .0001
def_text = files['def'].read_text()
unit = re.search(r'UNITS DISTANCE MICRONS (\d+)\s*;',def_text)
assert unit and int(unit[1]) == 2000, 'Reviewed DEF parser requires 2000 DBU/um'
section = re.search(r'\nNETS\s+(\d+)\s*;(.*?)\nEND NETS',def_text,re.S)
assert section
net_pat = re.compile(r'^\s*-\s+(\S+)\s+(.*?);\s*$',re.M|re.S)
entries = list(net_pat.finditer(section[2]))
assert len(entries) == int(section[1])
bodies = {m[1]:m[2] for m in entries}; assert len(bodies) == len(entries)
width = {n:int(w) for n,w in (line.split('\t') for line in files['layers'].read_text().splitlines())}
vias = {}; vlayers = {}
for line in files['vias'].read_text().splitlines():
    n,l,*b = line.split('\t'); assert len(b)==4
    vias.setdefault(n,[]).append((l,list(map(int,b))))
    if l.startswith('metal'): vlayers.setdefault(n,set()).add(l)
tree = ast.parse(files['parser'].read_text(encoding='utf-8-sig'))
functions = [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse']
assert len(functions)==1
fmt = lambda pt,e:'( '+str(pt[0])+' '+str(pt[1])+(' '+str(e) if e is not None else '')+' )'
exec(compile(ast.Module(body=functions,type_ignores=[]),str(files['parser']),'exec'))
rules = {'metal2':(13,.07),'metal3':(15,.07),'metal9':(27,.8),'metal10':(29,.8),'via9':(28,.88)}
cache = {}; rows = []
for index,match in enumerate(matches,1):
    kind,source,box,layer = match.groups()
    xy = re.findall(r'-?\d+(?:\.\d+)?',box)
    assert len(xy)==4, ('Unparsed bbox',box)
    xy = list(map(float,xy)); assert xy[0]<xy[2] and xy[1]<xy[3]
    row = dict(index=index,kind=kind,source=source,layer=layer,bbox_um=xy,
               disposition='unresolved',same_net_route_fully_covers_marker=False)
    if layer not in rules:
        row['reason']='Layer outside reviewed local checker'; rows.append(row); continue
    layer_num,spacing = rules[layer]
    li = layout.find_layer(layer_num,0); assert li is not None, ('Absent actual GDS layer',layer)
    marker = pya.Box(*[round(x/layout.dbu) for x in xy]); roi = marker.enlarged(round(2/layout.dbu))
    actual = pya.Region(top.begin_shapes_rec_overlapping(li,roi)) & pya.Region(roi); actual.merge()
    row['marker_fully_covered_by_actual_metal'] = (pya.Region(marker)-actual).is_empty()
    row['local_spacing_um'] = spacing
    row['actual_local_check'] = {
        name:[str(pair) for pair in check(round(spacing/layout.dbu)).each() if pair.bbox().touches(marker)]
        for name,check in [('space',actual.space_check),('notch',actual.notch_check)]}
    own = re.fullmatch(r'net:(\S+)',source)
    if own and own[1] in bodies:
        net=own[1]
        try:
            if net not in cache: cache[net]=parse(bodies[net])[0]
            own_box=pya.Box(*[round(x*2000) for x in xy])
            row['same_net_route_fully_covers_marker']=(pya.Region(own_box)-cache[net].get(layer,pya.Region())).is_empty()
            row['source_net']=net
        except Exception as error:
            row['route_parse_error']=str(error)
    # Only this reviewed lower-metal mechanism is explained automatically.
    # Upper/cut/other violation classes require their own physical resolution.
    if (kind=='Metal Spacing' and layer in ('metal2','metal3')
        and row['marker_fully_covered_by_actual_metal']
        and row['same_net_route_fully_covers_marker']
        and not any(row['actual_local_check'].values())):
        row['disposition']='explained_same_net_continuous_material'
    rows.append(row)
after = {p:sha(p) for p in initial}; assert after==initial, 'Input changed during checker'
(out/'inputs-after.json').write_text(json.dumps(after,indent=2))
unresolved=[r['index'] for r in rows if r['disposition']=='unresolved']
receipt=dict(accepted=False,candidate_id=spec['candidate_id'],
    scope='Per-marker native diagnosis only. Original full deck, PG/connectivity, STA, function and views remain independent mandatory gates.',
    native_markers_resolved=not unresolved,count=len(rows),
    dispositions=dict(collections.Counter(r['disposition'] for r in rows)),
    unresolved_indices=unresolved,inputs_sha256=initial,markers=rows,
    origin_receipts_require_aggregation_verification=True)
(out/'receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps({k:v for k,v in receipt.items() if k not in ('markers','inputs_sha256')},indent=2))
