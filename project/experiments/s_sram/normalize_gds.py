"""Reserialize the same bank into the standard-cell stream DBU, without ECO.

Read back every local mask, label and hierarchical instance in physical units.
The original qualified GDS remains immutable and is the geometry reference.
"""
import collections,hashlib,json,os
from pathlib import Path
import pya

assert os.environ.get('SLURM_JOB_ID')
source,output=map(Path,(SOURCE,OUTPUT));assert not output.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();initial=sha(source)
old=pya.Layout();old.read(str(source));assert old.dbu==.0005
options=pya.SaveLayoutOptions();options.dbu=.0001;old.write(str(output),options)
new=pya.Layout();new.read(str(output));assert new.dbu==.0001
assert {c.name for c in old.each_cell()}=={c.name for c in new.each_cell()}
def labels(cell,index,scale):
 rows=[]
 for shape in cell.shapes(index).each():
  if shape.is_text():
   t=shape.text;tr=t.trans
   rows.append((t.string,int(tr.disp.x*scale),int(tr.disp.y*scale),tr.angle,tr.is_mirror(),int(t.size*scale),t.font,t.halign,t.valign))
 return sorted(rows)
def instances(cell,scale):
 return collections.Counter((i.cell.name,tr.mag,tr.angle,tr.is_mirror(),int(tr.disp.x*scale),int(tr.disp.y*scale))for i in cell.each_inst()for tr in i.cell_inst.each_cplx_trans())
cells=0;mask_layers=0
for c in old.each_cell():
 other=new.cell(c.name);assert instances(c,5)==instances(other,1)
 for index in old.layer_indices():
  info=old.get_info(index);target=new.find_layer(info.layer,info.datatype);assert target is not None
  a=pya.Region(c.shapes(index)).transformed(pya.ICplxTrans(5,0,False,0,0)).merged();b=pya.Region(other.shapes(target)).merged()
  assert (a^b).is_empty(),(c.name,info.to_s())
  assert labels(c,index,5)==labels(other,target,1),(c.name,info.to_s(),'labels')
  mask_layers+=not a.is_empty()
 cells+=1
assert sha(source)==initial
Path(RECEIPT).write_text(json.dumps(dict(passed=True,qualified=False,scope='Lossless physical geometry/unit serialization only; original DRC/LVS and all whole-S gates remain required',source=str(source),source_sha256=initial,output=str(output),output_sha256=sha(output),source_dbu_um=old.dbu,target_dbu_um=new.dbu,cells=cells,nonempty_cell_layers=mask_layers,all_cell_masks_labels_and_instances_exact=True),indent=2)+'\n')
