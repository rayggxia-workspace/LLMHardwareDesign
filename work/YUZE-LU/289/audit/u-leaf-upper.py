import pya,json,hashlib
from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');c=r/'cu/runs/U-v7-macropdn-x8-seed0';merged=c/'flow/results/nangate45/u-overlay-current/base/6_final.gds'
sources={'local_s_base':Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base/6_final.gds'),'block_v2_e_compact':Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/release/e_compact/6_final.gds')}
a=pya.Layout();a.read(str(merged));results=[]
for name,path in sources.items():
 b=pya.Layout();b.read(str(path));ca=a.cell(name);cb=b.cell(name);assert ca is not None and cb is not None;assert a.dbu==b.dbu
 ai={(x.layer,x.datatype):a.find_layer(x) for x in a.layer_infos()};bi={(x.layer,x.datatype):b.find_layer(x) for x in b.layer_infos()};rows=[]
 for layer in sorted(set(ai)|set(bi)):
  if layer[0]<21:continue
  ra=pya.Region(ca.begin_shapes_rec(ai[layer])) if layer in ai else pya.Region();rb=pya.Region(cb.begin_shapes_rec(bi[layer])) if layer in bi else pya.Region()
  diff=ra^rb
  if not diff.is_empty():
   removed=rb-ra;added=ra-rb
   rows.append(dict(layer=layer,source_area_um2=rb.area()*b.dbu*b.dbu,merged_area_um2=ra.area()*a.dbu*a.dbu,removed_area_um2=removed.area()*a.dbu*a.dbu,added_area_um2=added.area()*a.dbu*a.dbu,removed_bbox=str(removed.bbox()),added_bbox=str(added.bbox()),removed_shapes=[str(p) for p in removed.each()][:20],added_shapes=[str(p) for p in added.each()][:20]))
 results.append(dict(cell=name,source=str(path),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),geometry_equal=not rows,differences=rows))
o=dict(merged=str(merged),merged_sha256=hashlib.sha256(merged.read_bytes()).hexdigest(),results=results)
(r/'audit/U-v7-leaf-source-upper-geometry.json').write_text(json.dumps(o,indent=2));print(json.dumps(o,indent=2))
