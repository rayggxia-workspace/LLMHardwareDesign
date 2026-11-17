"""Stream nine native base views and the verified M11/M12 overlay; no readers."""
from pathlib import Path
from collections import defaultdict
import csv,gzip,hashlib,json,sys
import pya
root=Path(root_dir);case=root/'final';sys.path.insert(0,str(root/'engine'))
from geometry import segment_shape,via_shapes
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=load(case/'spec.json');tech=spec['technology'];routes=load(case/'route.json')['routes']
place=load(case/'placement.json');lower=load(case/'lower-overlay.json')['by_terminal']
layout=pya.Layout();layout.dbu=.0001;scale=5
top=layout.create_cell('PR271_NINE_BASE_FOUR_LINKS')
overlay=layout.create_cell('M11_M12_SIGNAL_OVERLAY');top.insert(pya.CellInstArray(overlay.cell_index(),pya.Trans()))
layers={f'M{i}':9+2*i for i in range(1,11)};layers.update({f'V{i}':10+2*i for i in range(1,10)})
layers.update(V10=210,M11=211,V11=212,M12=213)
indices={k:layout.layer(v,0) for k,v in layers.items()};expected={}
def put(name,shapes):
 cell=layout.create_cell(name);overlay.insert(pya.CellInstArray(cell.cell_index(),pya.Trans()))
 grouped=defaultdict(pya.Region)
 for layer,box in shapes:grouped[layer].insert(pya.Box(*(v*scale for v in box)))
 for layer,region in grouped.items():
  region=region.merged();cell.shapes(indices[layer]).insert(region);expected[name,layer]=region
for i,(name,r) in enumerate(sorted(routes.items())):
 shapes=[segment_shape(s['layer'],s['a'],s['b'],tech) for s in r['segments']]
 shapes.extend(sh for p in r['via11'] for sh in via_shapes('via11',p,tech))
 shapes.extend(sh for v in r['via10'] for sh in via_shapes('via10',v['at'],tech))
 put(f'UPPER_{i:04d}_{name}',shapes)
order=('M7','M8','M9','M10','V7','V8','V9')
for i,(pin,shapes) in enumerate(sorted(lower.items())):put(f'LOWER_{i:04d}',[(order[k],b) for k,b in shapes])
mapping={f'metal{i}':f'M{i}' for i in range(7,11)};mapping.update({f'via{i}':f'V{i}' for i in range(7,10)})
native={};counts={}
for key in ('C','P2','P','U','F','J'):
 folder=case/('native-'+key);source=folder/'native.tsv.gz'
 cell=layout.create_cell('NATIVE_'+key+'_M7_M10');native[key]=cell;count=0
 with gzip.open(source,'rt') as f:
  for line in f:
   if line.startswith('#'):continue
   owner,layer,role,*box=line.split()
   if layer not in mapping or role.endswith('obs'):continue
   cell.shapes(indices[mapping[layer]]).insert(pya.Box(*(int(v)*scale for v in box)));count+=1
 counts[key]=count
base_cells=[]
for name,box in place['boxes_dbu'].items():
 key='C' if name=='C0' else 'P2' if name=='P2' else name[0]
 cell=layout.create_cell('BASE_'+name);cell.insert(pya.CellInstArray(native[key].cell_index(),pya.Trans()))
 x,y,r,t=box
 tr=pya.Trans(pya.Trans.M90,r*scale,y*scale) if name=='P1' else pya.Trans(x*scale,y*scale)
 top.insert(pya.CellInstArray(cell.cell_index(),tr));base_cells.append(cell.name)
 top.shapes(layout.layer(3000,0)).insert(pya.Box(*(v*scale for v in box)))
 top.shapes(layout.layer(3001,0)).insert(pya.Text(name,pya.Trans(x*scale+5000,y*scale+5000)))
assert len(base_cells)==9
out=case/'271-nine-native-four-links.oas';layout.write(str(out))
again=pya.Layout();again.read(str(out))
for (name,layer),reference in expected.items():
 observed=pya.Region(again.cell(name).begin_shapes_rec(again.find_layer(layers[layer],0)))
 assert (observed^reference).is_empty(),(name,layer)
# Exclude the upper via's own M10 pad from the supporting-copper proof.
support=pya.Region()
for name in base_cells:
 pass
for inst in again.cell(top.name).each_inst():
 cell=inst.cell
 if cell.name.startswith('BASE_'):
  reg=pya.Region(cell.begin_shapes_rec(again.find_layer(layers['M10'],0)))
  support+=reg.transformed(inst.trans)
for name,layer in expected:
 if name.startswith('LOWER_') and layer=='M10':support+=expected[name,layer]
cuts=pya.Region(again.cell(top.name).begin_shapes_rec(again.find_layer(layers['V10'],0)))
assert (cuts-support.merged()).is_empty(),'V10 cut without native/lower-adapter copper'
receipt={'compute_blocks':sorted(place['boxes_dbu']),'compute_block_count':9,'standalone_reader_blocks':[],
 'checked_top_nets':len(routes),'verified_contact_count':sum(len(r['via10']) for r in routes.values()),
 'shape_round_trip':True,'all_v10_cuts_enclosed_by_native_or_lower_adapter_m10':True,
 'native_rectangles_per_view':counts,'sha256':sha(out),
 'scope':'M11/M12 research-rule signal overlay and native M7-M10 abstract/exported geometry; not full-chip routed/signoff GDS'}
(case/'stream-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt),flush=True)
