"""Join actual native PG additions with the immutable accepted native GDS."""
import hashlib,json
from pathlib import Path
import pya
request=json.loads(Path('PG_ACCESS_MANIFEST_PLACEHOLDER').read_text());out=Path(request['out'])
assert hashlib.sha256(Path(request['native']).read_bytes()).hexdigest()==request['native_sha256']
original=pya.Layout();original.read(request['native']);assert len(original.top_cells())==1
layout=pya.Layout();layout.dbu=original.dbu
native=layout.create_cell('ACCEPTED_NATIVE');native.copy_tree(original.top_cell())
top=layout.create_cell('FIXED_PG_WRAPPER');top.insert(pya.CellInstArray(native.cell_index(),pya.Trans()))
mapping={**{'metal'+str(i):(9+2*i,0) for i in range(1,11)},**{'via'+str(i):(10+2*i,0) for i in range(1,10)}}
added={};expected=[]
for line in Path(request['geometry']).read_text().splitlines():
 net,layer,kind,*values=line.split('\t');assert net in ('VDD','VSS') and layer in mapping
 box=[v/2000/layout.dbu for v in map(int,values)];assert all(abs(v-round(v))<1e-7 for v in box)
 box=tuple(round(v) for v in box);pair=mapping[layer]
 shape=top.shapes(layout.layer(*pair)).insert(pya.Box(*box));shape.set_property(1,net)
 expected.append((*pair,box,net));added.setdefault(pair,pya.Region());added[pair].insert(pya.Box(*box))
assert expected
layout.write(str(out/'wrapper.gds'));read=pya.Layout();read.read(str(out/'wrapper.gds'));assert len(read.top_cells())==1
actual=[]
for index in read.layer_indexes():
 info=read.get_info(index)
 for shape in read.top_cell().shapes(index).each():
  assert shape.is_box();b=shape.box;actual.append((info.layer,info.datatype,(b.left,b.bottom,b.right,b.top),shape.property(1)))
assert sorted(actual)==sorted(expected),'GDS native PG additions differ from actual ODB geometry'
checks={}
pairs={(original.get_info(i).layer,original.get_info(i).datatype) for i in original.layer_indexes()}|set(added)
for pair in pairs:
 base=pya.Region(original.top_cell().begin_shapes_rec(original.layer(*pair)))
 wanted=base+added.get(pair,pya.Region())
 observed=pya.Region(read.top_cell().begin_shapes_rec(read.layer(*pair)))
 checks[str(pair)]=not any(True for _ in (wanted^observed).each());assert checks[str(pair)]
(out/'gds-readback.json').write_text(json.dumps(dict(passed=True,actual_added_shapes=len(actual),native_plus_fixed_additions_xor=checks,
 scope='Exact GDS native-plus-declared-fixed-PG geometry. Full DRC, supply continuity and fresh RC/STA remain independent.'),indent=2)+'\n')
