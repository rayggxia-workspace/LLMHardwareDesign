import pya,json,collections
from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');merged=r/'cu/runs/U-v7-macropdn-x8-seed0/flow/results/nangate45/u-overlay-current/base/6_final.gds'
l=pya.Layout();l.read(str(merged));top=l.cell('u_n32_controlled_dma_64')
rows=json.loads((r/'audit/U-v7-full-localization-v2.json').read_text())['markers'];out=[]
for name in ('local_s_base','block_v2_e_compact'):
 c=l.cell(name);insts=[i for i in top.each_inst() if i.cell_index==c.cell_index()];assert len(insts)==1;inst=insts[0]
 for cat,layer,distance in [("'VIA6.2'",22,.16),("'VIA6.2'",24,.44),("'METAL9.2'",27,.8),("'VIA9.2'",28,.88)]:
  idx=l.find_layer(layer,0);source=pya.Region(c.begin_shapes_rec(idx)).merged();checks=source.space_check(round(distance/l.dbu),False,pya.Region.Euclidian)
  full=pya.Region(top.begin_shapes_rec(idx));known=pya.Region()
  for mi in top.each_inst():
   if l.cell(mi.cell_index).name in ('local_s_base','block_v2_e_compact','n_s32_u39_rms'):
    known+=pya.Region(l.cell(mi.cell_index).begin_shapes_rec(idx)).transformed(mi.trans)
  parent_only=full-known
  markers=[]
  for row in rows:
   if row['report_cell']!=name or row['category']!=cat:continue
   box=pya.Box(*[round(x/l.dbu) for x in row['bbox']]).enlarged(round(.1/l.dbu));parent=parent_only&pya.Region(box)
   markers.append(dict(local_bbox=row['local_bbox'],parent_bbox=row['bbox'],parent_direct_area_um2=parent.area()*l.dbu*l.dbu,parent_polygons=[str(p) for p in parent.each()]))
  out.append(dict(cell=name,category=cat,actual_gds_layer=layer,threshold_um=distance,standalone_source_spacing_errors=checks.count(),source_error_pairs=[str(e) for e in checks.each()],parent_context=markers))
(r/'audit/U-v7-leaf-context-v2.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
