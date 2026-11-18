import pya,json,re,collections,xml.etree.ElementTree as E
from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');c=r/'cu/runs/U-v7-macropdn-x8-seed0';l=pya.Layout();l.read(str(c/'flow/results/nangate45/u-overlay-current/base/6_final.gds'));top=l.cell('u_n32_controlled_dma_64')
macros=[]
for inst in top.each_inst():
 name=l.cell(inst.cell_index).name
 if name in ('n_s32_u39_rms','local_s_base','block_v2_e_compact','s_sram_256x128_freepdk45'):
  box=inst.bbox();macros.append(dict(name=name,bbox=[box.left*l.dbu,box.bottom*l.dbu,box.right*l.dbu,box.top*l.dbu],transform=str(inst.trans),dx_um=inst.trans.disp.x*l.dbu,dy_um=inst.trans.disp.y*l.dbu,rotation=inst.trans.angle,mirror=inst.trans.is_mirror()))
rows=[]
for item in E.parse(str(c/'signoff/full.lyrdb')).findall('.//items/item'):
 cat=item.findtext('category');cell=item.findtext('cell');value=item.findtext('values/value')
 xy=[tuple(map(float,m)) for m in re.findall(r'(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)',value)]
 if not xy:raise ValueError(value)
 box=[min(x for x,y in xy),min(y for x,y in xy),max(x for x,y in xy),max(y for x,y in xy)]
 original_box=box[:]
 if cell!=top.name:
  owners=[m for m in macros if m['name']==cell]
  if len(owners)==1 and owners[0]['rotation']==0 and not owners[0]['mirror']:
   o=owners[0];box=[box[0]+o['dx_um'],box[1]+o['dy_um'],box[2]+o['dx_um'],box[3]+o['dy_um']]
 hits=[m['name'] for m in macros if not (box[2]<m['bbox'][0] or box[0]>m['bbox'][2] or box[3]<m['bbox'][1] or box[1]>m['bbox'][3])]
 rows.append(dict(category=cat,report_cell=cell,local_bbox=original_box,bbox=box,macro_bbox_intersections=hits,geometry=value))
summary=collections.Counter((x['category']+' @ '+x['report_cell'],','.join(x['macro_bbox_intersections']) or 'outside_macro_bbox') for x in rows)
o=dict(scope='BBox localization only, not metal/net ownership or waiver',macro_instances=macros,summary=[dict(category=a,location=b,count=n) for (a,b),n in summary.items()],markers=rows)
(r/'audit/U-v7-full-localization.json').write_text(json.dumps(o,indent=2));print(json.dumps(dict(macro_instances=macros,summary=o['summary']),indent=2))
