from pathlib import Path
import re,json,hashlib,pya
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');out=Path.cwd()
old=r/'cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.def'
sources=[r/('cu/runs/C-v28-actual-i'+str(i)+'-h50/legalized.def') for i in (8,16)]
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/gds/NangateOpenCellLibrary.gds')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=[old,*sources,lib,Path(__file__)];before={str(p):sha(p) for p in files}
assert sha(lib)=='7fdbd7f4e46283fdd9b9a369e1cae1a7f6f742c8e75cfe943c17f451626fe8e8'
def components(path):
 text=path.read_text();m=re.search(r'\nCOMPONENTS\s+(\d+)\s*;(.*?)\nEND COMPONENTS',text,re.S);assert m
 entries=re.findall(r'^\s*-\s+(\S+)\s+(\S+)\s+.*?;',m[2],re.M|re.S)
 assert len(entries)==int(m[1]);d=dict(entries);assert len(d)==len(entries);return d
baseline=components(old);changed={};selected=set()
for source in sources:
 current=components(source)
 changes=[dict(instance=n,before=baseline.get(n),after=m) for n,m in current.items() if baseline.get(n)!=m]
 changed[str(source)]=changes;selected.update(x['after'] for x in changes)
layout=pya.Layout();layout.read(str(lib));cells={c.name:c for c in layout.each_cell()}
missing=selected-cells.keys();assert not missing, ('Changed non-library master requires separate review',missing)
assert selected and 'OAI221_X4' not in selected
top=layout.create_cell('C_V28_CHANGED_STANDARD_CELLS_ONLY');placements=[]
pitch=round(100/layout.dbu)
for i,name in enumerate(sorted(selected)):
 c=cells[name];box=c.bbox();assert box.width()<pitch//2 and box.height()<pitch//2
 x=(i%8)*pitch-box.left;y=(i//8)*pitch-box.bottom
 top.insert(pya.CellInstArray(c.cell_index(),pya.Trans(x,y)))
 placements.append(dict(master=name,translation_dbu=[x,y],bbox_dbu=str(box)))
options=pya.SaveLayoutOptions();options.select_cell(top.cell_index());target=out/'fixture.gds';layout.write(str(target),options)
# Readback every recursive layer union, hierarchy placements, and text geometry are
# retained by copying original cells unchanged; fixture adds translation refs only.
check=pya.Layout();check.read(str(target));ct=check.top_cell();assert ct.name==top.name
assert len(list(ct.each_inst()))==len(selected)
for name in selected:
 a=cells[name];b=check.cell(name);assert b is not None
 for li in layout.layer_indexes():
  info=layout.get_info(li);other=check.find_layer(info.layer,info.datatype)
  aa=pya.Region(a.begin_shapes_rec(li))
  bb=pya.Region(b.begin_shapes_rec(other)) if other is not None else pya.Region()
  assert (aa^bb).is_empty(), (name,str(info))
assert before=={str(p):sha(p) for p in files}
(out/'export-binding.json').write_text(json.dumps(dict(scope='Changed/added standard-cell masters from i8/i16 h50 legalized DEF versus frozen v27; translation-only separated library fixture, no macros.',inputs_sha256=before,changed_instances=changed,masters=sorted(selected),placements=placements,gds_sha256=sha(target),recursive_material_readback_exact=True),indent=2))
print(json.dumps(dict(master_count=len(selected),masters=sorted(selected)),indent=2))
