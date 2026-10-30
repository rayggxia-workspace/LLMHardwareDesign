import pya,json,hashlib
from pathlib import Path
layouts=[]
for stage in ('before','after'):
 p=Path(stage)/'gds-flow/results/nangate45/bv1_block_v1_v/base/6_final.gds';l=pya.Layout();l.read(str(p));assert len(l.top_cells())==1;layouts.append(l)
a,z=layouts;assert a.dbu==z.dbu
pairs=sorted(set((i.layer,i.datatype)for l in layouts for i in l.layer_infos()));rows=[]
for pair in pairs:
 regs=[]
 for l in layouts:
  i=l.find_layer(*pair);r=pya.Region()if i is None else pya.Region(l.top_cell().begin_shapes_rec(i));r.merge();regs.append(r)
 diff=regs[0]^regs[1];count=sum(1 for _ in diff.each());rows.append(dict(layer=pair,xor_polygons=count,before_area=regs[0].area(),after_area=regs[1].area()));assert count==0,(pair,count)
json.dump(dict(passed=True,all_recursive_non_text_layer_union_xor_zero=True,dbu_um=a.dbu,layers=rows,scope='Actual complete before/after GDS independently streamed from exact451 DEF including all library cells, cuts and masks; fullhierarchy materialized XOR. Identity, not qualification.'),open('full-mask-xor.json','w'),indent=2)
