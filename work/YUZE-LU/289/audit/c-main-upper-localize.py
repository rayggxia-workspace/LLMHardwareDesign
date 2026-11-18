from pathlib import Path
import pya,json,re,collections,hashlib,xml.etree.ElementTree as E
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');out=r/'audit/C-main-clock4-physical-v1';gds=r/'cu/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base/6_final.gds';report=out/'focused/upper.lyrdb'
l=pya.Layout();l.read(str(gds));top=l.cell('cfj_group_c_memory_legacy');names={'block_v2_e_compact','e_s32_pipeline_128','block_v2_g','r_stream_local','local_s_base'};macros=[]
for inst in top.each_inst():
 name=l.cell(inst.cell_index).name
 if name in names:
  assert inst.trans.angle==0 and not inst.trans.is_mirror()
  b=inst.bbox();macros.append(dict(name=name,bbox=[b.left*l.dbu,b.bottom*l.dbu,b.right*l.dbu,b.top*l.dbu],dx_um=inst.trans.disp.x*l.dbu,dy_um=inst.trans.disp.y*l.dbu))
assert len(macros)==5
rows=[]
for i,it in enumerate(E.parse(str(report)).findall('.//items/item')):
 cat=it.findtext('category');cell=it.findtext('cell');vs=[v.text for v in it.findall('values/value')];xy=[tuple(map(float,x)) for v in vs for x in re.findall(r'(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)',v)];assert xy
 b=[min(x for x,y in xy),min(y for x,y in xy),max(x for x,y in xy),max(y for x,y in xy)];local=b[:]
 if cell!=top.name:
  owners=[m for m in macros if m['name']==cell];assert len(owners)==1;o=owners[0];b=[b[0]+o['dx_um'],b[1]+o['dy_um'],b[2]+o['dx_um'],b[3]+o['dy_um']]
 b=[round(x,6) for x in b];hits=[m['name'] for m in macros if not(b[2]<m['bbox'][0] or b[0]>m['bbox'][2] or b[3]<m['bbox'][1] or b[1]>m['bbox'][3])]
 rows.append(dict(id=i,category=cat,report_cell=cell,local_bbox=local,bbox=b,macro_bbox_intersections=hits,geometry=vs))
groups=collections.defaultdict(list)
for m in rows:groups[m['category'],tuple(m['bbox'])].append(m['id'])
v=dict(scope='Actual hierarchy bbox localization and exact category/bbox duplicate grouping only; no metal ownership or waiver',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (gds,report,Path(__file__))},macro_instances=macros,report_items=len(rows),unique_category_bbox=len(groups),summary=dict(collections.Counter(str((m['category'],','.join(m['macro_bbox_intersections']))) for m in rows)),duplicate_groups=[dict(category=k[0],bbox=k[1],report_ids=ids) for k,ids in groups.items() if len(ids)>1],markers=rows)
(out/'upper-localization.json').write_text(json.dumps(v,indent=2));print(json.dumps({k:v[k] for k in ('report_items','unique_category_bbox','summary')},indent=2))
