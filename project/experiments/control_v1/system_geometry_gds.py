"""Independent full-composition GDS mask, rule and electrical-tree readback."""
import hashlib,json
from pathlib import Path
import pya
request=json.loads(Path('INPUT_MANIFEST_PLACEHOLDER').read_text());folder=Path(request['output']).parent
fixture=json.loads(Path(request['fixture']).read_text());layout=pya.Layout();layout.dbu=.001
top=layout.create_cell('CONTROL_SYSTEM_25');native_layers=set();expected_native={}
for label,row in request['native'].items():
 assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
 source=pya.Layout();source.read(row['path']);assert len(source.top_cells())==1
 cell=layout.create_cell('FROZEN_'+label);cell.copy_tree(source.top_cell())
 x,y=fixture['placements_um'][label];transform=pya.Trans(round(x/layout.dbu),round(y/layout.dbu))
 top.insert(pya.CellInstArray(cell.cell_index(),transform))
 for idx in source.layer_indexes():
  info=source.get_info(idx);pair=(info.layer,info.datatype);native_layers.add(pair)
 for idx in layout.layer_indexes():
  info=layout.get_info(idx);pair=(info.layer,info.datatype)
  region=pya.Region(cell.begin_shapes_rec(idx)).transformed(transform)
  expected_native.setdefault(pair,pya.Region());expected_native[pair]+=region
mapping={'metal10':(29,0),'via10':(210,0),'metal11':(211,0),'via11':(212,0),'metal12':(213,0)}
assert not native_layers.intersection(set(mapping.values())-{(29,0)})
def unit(v):
 value=v/2000/layout.dbu;assert abs(value-round(value))<1e-6;return round(value)
expected=[]
for s in fixture['shapes']:
 if s['layer']=='metal10':continue
 pair=mapping[s['layer']];b=tuple(unit(v) for v in s['box_dbu']);shape=top.shapes(layout.layer(*pair)).insert(pya.Box(*b));shape.set_property(1,s['net']);expected.append((*pair,b,s['net']))
layout.write(request['output']);read=pya.Layout();read.read(request['output']);assert len(read.top_cells())==1
observed=[];regions={};net_regions={}
for layer,pair in mapping.items():
 index=read.layer(*pair);regions[layer]=pya.Region(read.top_cell().begin_shapes_rec(index));regions[layer].merge()
 if layer=='metal10':continue
 for shape in read.top_cell().shapes(index).each():
  assert shape.is_box();b=shape.box;net=shape.property(1);observed.append((*pair,(b.left,b.bottom,b.right,b.top),net))
  net_regions.setdefault((net,layer),pya.Region());net_regions[net,layer].insert(b)
assert sorted(expected)==sorted(observed),'GDS changed net identity or upper rectangles'
def empty(region):return not any(True for _ in region.each())
native_checks={}
for pair in sorted(native_layers):
 before=expected_native[pair];after=pya.Region(read.top_cell().begin_shapes_rec(read.layer(*pair)))
 native_checks[str(pair)]=empty(before^after);assert native_checks[str(pair)],('Changed frozen native layer',pair)
checks={}
for layer in ['metal11','metal12']:
 checks[layer+'_width']=empty(regions[layer].width_check(round(2/read.dbu)))
 checks[layer+'_spacing']=empty(regions[layer].space_check(round(2/read.dbu)))
for via,lower,upper in [('via10','metal10','metal11'),('via11','metal11','metal12')]:
 checks[via+'_spacing']=empty(regions[via].space_check(round(2.2/read.dbu)))
 checks[via+'_lower_enclosure']=empty(regions[via]-regions[lower]);checks[via+'_upper_enclosure']=empty(regions[via]-regions[upper])
 checks[via+'_exact_cut']=all(b[2]-b[0]==round(2/read.dbu) and b[3]-b[1]==round(2/read.dbu) for l,d,b,n in observed if (l,d)==mapping[via])
# Reconstruct connectivity from actual GDS rectangles/cuts, independently of
# the search branch lists. Fixed four-micron tracks make all wire edges exact.
import collections
adj=collections.defaultdict(lambda:collections.defaultdict(set));occupancy={}
def occupy(vertex,net):
 assert occupancy.setdefault(vertex,net)==net,('Actual cross-net short',net,vertex)
def lattice(v,phase):
 assert (v-phase)%4000==0,(v,phase)
 return (v-phase)//4000
for layer_number,datatype,b,net in observed:
 layer=next(name for name,pair in mapping.items() if pair==(layer_number,datatype))
 if layer in ('metal11','metal12'):
  x0,x1=lattice(b[0]+1000,95),lattice(b[2]-1000,95)
  y0,y1=lattice(b[1]+1000,70),lattice(b[3]-1000,70)
  assert x0==x1 or y0==y1,'Non-Manhattan rectangle'
  level=0 if layer=='metal11' else 1
  for x in range(x0,x1+1):
   for y in range(y0,y1+1):
    v=(x,y,level);occupy(v,net)
    adj[net][v]
    if x>x0:w=(x-1,y,level);adj[net][v].add(w);adj[net][w].add(v)
    if y>y0:w=(x,y-1,level);adj[net][v].add(w);adj[net][w].add(v)
 else:
  assert layer in ('via10','via11')
  x,y=lattice((b[0]+b[2])//2,95),lattice((b[1]+b[3])//2,70)
  lo,hi=(-1,0) if layer=='via10' else (0,1)
  v,w=(x,y,lo),(x,y,hi)
  for vertex in (v,w):occupy(vertex,net)
  adj[net][v].add(w);adj[net][w].add(v)
assert set(adj)==set(fixture['terminals'])
for net,points in fixture['terminals'].items():
 targets=[]
 for point,kind in zip(points,fixture['terminal_kinds'][net]):
  x,y=lattice(unit(point[0]),95),lattice(unit(point[1]),70)
  targets.append((x,y,-1 if kind=='native' else 0))
 seen={targets[0]};todo=list(seen)
 while todo:
  for w in adj[net][todo.pop()]:
   if w not in seen:seen.add(w);todo.append(w)
 assert all(v in seen for v in targets) and seen==set(adj[net]),('Actual GDS open/disconnected stub',net)
checks['all_boundary_sinks_connected']=True
checks['independent_actual_cross_net_occupancy']=True
assert all(checks.values()),('Actual upper geometry design-rule failure',checks)
# Negative controls exercise the same native XOR, cut enclosure and net-short checks.
native_negative=not empty(expected_native[(29,0)]^(expected_native[(29,0)]|pya.Region(pya.Box(-10000,-10000,-8000,-8000))))
via_negative=not empty((regions['via10']|pya.Region(pya.Box(-10000,-10000,-8000,-8000)))-regions['metal10'])
short_negative=False
try:occupy(next(iter(occupancy)),'__negative_foreign_net__')
except AssertionError:short_negative=True
assert native_negative and via_negative and short_negative
result=dict(passed=True,connected_signal_nets=fixture['net_count'],physical_instances=fixture['instance_count'],native_masks_xor_zero=native_checks,upper_gds_exact_identity=True,checks=checks,
 negative_controls=dict(native_mask_change_rejected=native_negative,unlanded_via_rejected=via_negative,different_net_overlap_rejected=short_negative),
 scope=str(fixture['instance_count'])+' complete immutable native scenes and every extracted boundary signal/clock/reset wire. Actual GDS cut/metal connectivity and native XOR only. PG, calibrated RC and combined STA are separate mandatory gates.',system_pg_qualified=False,whole_system_qualified=False)
(folder/'joined-readback.json').write_text(json.dumps(result,indent=2)+'\n')
view=pya.LayoutView();view.load_layout(request['output'],0);view.max_hier();view.add_missing_layers();view.zoom_fit();view.save_image(str(folder/'layout.png'),1800,1200)
