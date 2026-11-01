"""Deterministic physical ECO of four 65nm VIA2 contact masters to 70nm.
Run with KLayout Python. Does not modify the source GDS, SPICE, pins or rules.
Expands their M2/M3 long-axis pads by 2.5nm/side to retain 35nm enclosure.
Requires independent full native DRC and transistor LVS after this operation.
"""
import pya,json,hashlib,os
from pathlib import Path
assert os.environ.get('SLURM_JOB_ID')
src=Path(SOURCE);out=Path(OUTPUT);assert not out.exists()
l=pya.Layout();l.read(str(src));assert l.dbu==0.0005
names=['s_sram_256x128_freepdk45_contact_'+str(n) for n in (7,18,20,27)]
def signature(db):
 result={}
 for c in db.each_cell():
  layers={db.get_info(i).to_s():sorted(s.to_s() for s in c.shapes(i).each()) for i in db.layer_indexes() if not c.shapes(i).is_empty()}
  insts=sorted((i.cell.name,i.cplx_trans.to_s(),i.a.to_s(),i.b.to_s(),i.na,i.nb) for i in c.each_inst())
  result[c.name]=dict(layers=layers,instances=insts)
 return result
before=signature(l);top_bbox=l.top_cell().bbox().to_s();edits=[]
for name in names:
 c=l.cell(name);assert c is not None
 for layer in (13,14,15):
  shapes=list(c.shapes(l.find_layer(layer,0)).each());assert len(shapes)==1 and shapes[0].is_box()
  shape=shapes[0];b=shape.box
  if layer==14:
   assert b.width()==b.height()==130
   new=b.enlarged(5)
  else:
   assert sorted([b.width(),b.height()])==[140,270]
   new=pya.Box(b.left-5,b.bottom,b.right+5,b.top) if b.width()>b.height() else pya.Box(b.left,b.bottom-5,b.right,b.top+5)
  edits.append(dict(cell=name,layer=layer,old=b.to_s(),new=new.to_s()))
  shape.box=new
assert l.top_cell().bbox().to_s()==top_bbox
expected=signature(l)
assert set(before)==set(expected)
for name in before:
 assert before[name]['instances']==expected[name]['instances']
 changed={k for k in set(before[name]['layers'])|set(expected[name]['layers']) if before[name]['layers'].get(k)!=expected[name]['layers'].get(k)}
 assert changed==({'13/0','14/0','15/0'} if name in names else set()),(name,changed)
l.write(str(out));r=pya.Layout();r.read(str(out));assert signature(r)==expected and r.dbu==l.dbu
record=dict(qualified=False,scope='Physical contact ECO only; separate full native DRC and transistor LVS required before use',source=str(src),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),output=str(out),output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),dbu_um=l.dbu,top_bbox=top_bbox,edits=edits,all_other_cell_geometry_layers_instances_and_text_unchanged=True,serialized_readback_exact=True)
Path(RECEIPT).write_text(json.dumps(record,indent=2)+'\n')
