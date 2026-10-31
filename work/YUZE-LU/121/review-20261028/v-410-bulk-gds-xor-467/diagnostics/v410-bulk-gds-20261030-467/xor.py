import pya,json,hashlib
from pathlib import Path
paths=[Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-via-gds-20261030-452/before/gds-flow/results/nangate45/bv1_block_v1_v/base/6_final.gds'),Path('gds-flow/results/nangate45/bv1_block_v1_v/base/6_final.gds')];layouts=[]
for p in paths:
 l=pya.Layout();l.read(str(p));assert len(l.top_cells())==1;layouts.append(l)
a,z=layouts;assert a.dbu==z.dbu;rows=[]
for pair in sorted(set((i.layer,i.datatype)for l in layouts for i in l.layer_infos())):
 regs=[]
 for l in layouts:
  i=l.find_layer(*pair);v=pya.Region()if i is None else pya.Region(l.top_cell().begin_shapes_rec(i));v.merge();regs.append(v)
 d=regs[0]^regs[1];count=sum(1 for _ in d.each());rows.append(dict(layer=pair,xor_polygons=count,before_area=regs[0].area(),after_area=regs[1].area()));assert count==0,(pair,count)
json.dump(dict(passed=True,all_recursive_non_text_layer_union_xor_zero=True,dbu_um=a.dbu,layers=rows,gds_sha256=[hashlib.sha256(p.read_bytes()).hexdigest()for p in paths],scope='Actual fullhierarchy GDS mask XOR for all191 nets/194 via realization definitions. Reused452 before GDS has exact byte-bound identical source DEF. No P&R rerun or duplicated before stream; no deck/STA/function qualification or transfer to463.'),open('full-mask-xor.json','w'),indent=2)
