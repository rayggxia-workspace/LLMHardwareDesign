"""Losslessly expose the global well union at the stream's root cell.

KLayout deep well self-separation reports six cross-cell row-corner artifacts;
the same exact masks in flat mode report zero. Keep all original cells and
well masks and add the identical union at the root. The unchanged full deep
deck still runs. No material, circuit, placement or routed wire changes.
"""
import collections,hashlib,json,os
from pathlib import Path
import pya

assert os.environ.get('SLURM_JOB_ID')
source,output=map(Path,(SOURCE,OUTPUT));assert not output.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();initial=sha(source)
old=pya.Layout();old.read(str(source));assert old.dbu==.0001
new=pya.Layout();new.read(str(source));root=new.top_cell();wells={}
for number in [2,3]:
    index=new.find_layer(number,0)
    original=pya.Region(root.begin_shapes_rec(index)).merged();assert not original.is_empty()
    wells[number]=original
    root.shapes(index).insert(original)
new.write(str(output));check=pya.Layout();check.read(str(output));assert check.dbu==old.dbu
assert {c.name for c in old.each_cell()}=={c.name for c in check.each_cell()}
assert old.top_cell().name==check.top_cell().name

def labels(cell,index):
    result=[]
    for s in cell.shapes(index).each():
        if not s.is_text():continue
        t=s.text;tr=t.trans
        result.append((t.string,tr.disp.x,tr.disp.y,tr.angle,tr.is_mirror(),t.size,t.font,t.halign,t.valign))
    return sorted(result)

def instances(cell):
    return collections.Counter((i.cell.name,tr.mag,tr.angle,tr.is_mirror(),tr.disp.x,tr.disp.y)
      for i in cell.each_inst()for tr in i.cell_inst.each_cplx_trans())

def shapes(cell,index):
    return collections.Counter(s.to_s()for s in cell.shapes(index).each()if not s.is_text())

for c in old.each_cell():
    other=check.cell(c.name);assert instances(c)==instances(other),c.name
    for index in old.layer_indices():
        info=old.get_info(index);target=check.find_layer(info.layer,info.datatype);assert target is not None
        assert labels(c,index)==labels(other,target),(c.name,info.to_s(),'labels')
        if c.name==root.name and info.datatype==0 and info.layer in [2,3]:continue
        assert shapes(c,index)==shapes(other,target),(c.name,info.to_s(),'mask shape')
for number,original in wells.items():
    actual=pya.Region(check.top_cell().begin_shapes_rec(check.find_layer(number,0))).merged()
    assert (original^actual).is_empty(),number
assert sha(source)==initial
Path(RECEIPT).write_text(json.dumps(dict(passed=True,qualified=False,source=str(source),source_sha256=initial,
 output=str(output),output_sha256=sha(output),dbu_um=old.dbu,all_global_physical_masks_identical=True,
 original_cell_names_instances_labels_and_nonroot_masks_unchanged=True,
 root_nonwell_geometry_unchanged=True,well_layers=[2,3],
 scope='Mask-identical hierarchical serialization; not an ECO, waiver or replacement DRC. Original full FEOL/BEOL/OFFGRID/ANTENNA deep deck remains mandatory.'),indent=2)+'\n')
