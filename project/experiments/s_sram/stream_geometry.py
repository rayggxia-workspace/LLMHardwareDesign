"""Independent DEF-unit/placement and original-bank-mask checks in KLayout.

All physical instances must agree, including fillers and taps. Rejects the
real mixed-reader-DBU failure even when routed ODB checks separately pass.
"""
import collections,hashlib,json,os,re
from pathlib import Path
import pya

assert os.environ.get('SLURM_JOB_ID')
definition,gds,bank=map(Path,(DEFINITION,GDS,BANK_GDS));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=dict(passed=False,qualified=False,inputs={str(p):sha(p)for p in [definition,gds,bank]})
try:
 text=definition.read_text();units=re.search(r'UNITS DISTANCE MICRONS (\d+)\s*;',text);assert units and int(units.group(1))==2000
 m=re.search(r'(?s)\bCOMPONENTS\s+(\d+)\s*;(.*?)\bEND COMPONENTS\b',text);assert m
 orient={'N':(0,False),'S':(180,False),'W':(90,False),'E':(270,False),'FN':(180,True),'FS':(0,True),'FW':(90,True),'FE':(270,True)}
 expected=collections.Counter();names=set();def_components={}
 for entry in m.group(2).split(';'):
  if not entry.strip():continue
  match=re.fullmatch(r'\s*-\s+(\S+)\s+(\S+).*?\+\s+(?:PLACED|FIXED|COVER)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)\s*',entry,re.S);assert match,entry[:100]
  name,master,x,y,o=match.groups();assert name not in names;names.add(name);angle,mirror=orient[o]
  def_components[name]=(master,int(x),int(y),angle,mirror)
 inventory=Path(NATIVE_INVENTORY);odb=Path(ODB)
 r['inputs'][str(inventory)]=sha(inventory);r['inputs'][str(odb)]=sha(odb)
 native_orient={'R0':(0,False),'R90':(90,False),'R180':(180,False),'R270':(270,False),'MX':(0,True),'MY':(180,True),'MXR90':(90,True),'MYR90':(270,True)}
 seen=set()
 for line in inventory.read_text().splitlines():
  name,master,ox,oy,o,x,y=line.split('\t');assert name not in seen;seen.add(name)
  # DEF escapes identifier punctuation; normalize only when the literal name
  # is absent, then require an exact unique native component correspondence.
  key=name if name in def_components else next((n for n in def_components if re.sub(r'\\(.)',r'\1',n)==name),None)
  assert key is not None
  angle,mirror=native_orient[o];assert def_components[key]==(master,int(x),int(y),angle,mirror)
  expected[(master,int(ox),int(oy),angle,mirror)]+=1
 assert len(seen)==len(names)==sum(expected.values())==int(m.group(1))
 layout=pya.Layout();layout.read(str(gds));assert layout.dbu==.0005 and len(layout.top_cells())==1
 top=layout.top_cell();assert top.name=='block_feed_s_macro_sram'
 actual=collections.Counter()
 masters={key[0]for key in expected}
 via_section=re.search(r'(?s)\bVIAS\s+\d+\s*;(.*?)\bEND VIAS\b',text)
 via_names=set(re.findall(r'(?m)^\s*-\s+(\S+)',via_section.group(1)))if via_section else set()
 tech=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef')
 r['inputs'][str(tech)]=sha(tech)
 via_names.update(re.findall(r'(?m)^VIA\s+(\S+)',tech.read_text()))
 auxiliary={f'VIA_{name}'for name in via_names};via_count=0
 for inst in top.each_inst():
  if inst.cell.name not in masters:
   assert inst.cell.name in auxiliary,('Unexpected noncomponent GDS instance',inst.cell.name)
   via_count+=sum(1 for _ in inst.cell_inst.each_cplx_trans());continue
  for tr in inst.cell_inst.each_cplx_trans():
   assert tr.mag==1 and abs(tr.angle-round(tr.angle))<1e-9
   actual[(inst.cell.name,int(tr.disp.x),int(tr.disp.y),round(tr.angle),tr.is_mirror())]+=1
 r.update(expected_instances=sum(expected.values()),actual_instances=sum(actual.values()),native_via_auxiliary_instances=via_count,
          missing_sample=list((expected-actual).items())[:8],extra_sample=list((actual-expected).items())[:8])
 assert actual==expected,'GDS instance positions/orientations/counts differ from native DEF physical units'
 source=pya.Layout();source.read(str(bank));assert source.dbu==layout.dbu
 original=source.top_cell();merged=layout.cell(original.name);assert merged is not None
 layers=[]
 for index in source.layer_indices():
  info=source.get_info(index);other=layout.find_layer(info.layer,info.datatype)
  original_region=pya.Region(original.begin_shapes_rec(index)).merged()
  if original_region.is_empty():continue
  assert other is not None
  merged_region=pya.Region(merged.begin_shapes_rec(other)).merged()
  assert (original_region^merged_region).is_empty(),info.to_s()
  layers.append(info.to_s())
 assert layers and sum(v for k,v in actual.items()if k[0]==original.name)==4
 assert all(sha(Path(p))==h for p,h in r['inputs'].items())
 r.update(passed=True,all_native_component_placements_exact=True,four_original_bank_masks_exact=True,bank_layers=layers,top_bbox_um=top.dbbox().to_s(),dbu_um=layout.dbu)
except Exception as e:r['failure']=repr(e);raise
finally:Path(RECEIPT).write_text(json.dumps(r,indent=2)+'\n')
