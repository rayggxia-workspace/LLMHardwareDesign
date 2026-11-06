"""Price real M3 landing metal into routed ODB before final RC extraction.

The bank's contact strip extends 2.5nm past its square pin. A route joining
the square can leave an illegal notch against that strip. Cover each proven
isolated signal landing with a grid-legal rectangle on the same actual net.
Bank masks, circuits, library and pin abstractions remain immutable.
Run allocated KLayout with GDS, LEF, OUTPUT and RECEIPT -rd arguments.
"""
import hashlib,json,math,os,re
from pathlib import Path
import pya

assert os.environ.get('SLURM_JOB_ID')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
l=pya.Layout();l.read(GDS)
actual=pya.Region(l.top_cell().begin_shapes_rec(l.find_layer(15,0))).merged()
text=Path(LEF).read_text();patches=[];edits=[];rect=r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;'
for pin in re.finditer(r'(?ms)^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$',text):
    if pin.group(1) in ('vdd','gnd'):continue
    windows=pya.Region()
    for part in re.finditer(r'(?s)LAYER\s+metal3\s*;(.*?)(?=\bLAYER\b|\bEND\b|\Z)',pin.group(2)):
        for m in re.finditer(rect,part.group(1)):
            windows.insert(pya.DBox(*map(float,m.groups())).to_itype(l.dbu))
    if windows.is_empty():continue
    assert (windows-actual).is_empty()
    connected=actual.interacting(windows)
    assert connected.count()==1
    box=connected.bbox().to_dtype(l.dbu)
    assert box.width()<1 and box.height()<1,(pin.group(1),str(box))
    coords=[math.floor((v+1e-9)/.005)*.005-.005 for v in [box.left,box.bottom]]
    coords += [math.ceil((v-1e-9)/.005)*.005+.005 for v in [box.right,box.top]]
    patch=pya.Region(pya.DBox(*coords).to_itype(l.dbu))
    assert (connected-patch).is_empty()
    assert (patch.sized(round(.070/l.dbu))&(actual-connected)).is_empty(),pin.group(1)
    parts=list(re.finditer(r'(?s)LAYER\s+metal3\s*;(.*?)(?=\bLAYER\b|\bEND\b|\Z)',pin.group(2)))
    assert len(parts)==1
    part=parts[0];start=pin.start(2)+part.start(1);end=pin.start(2)+part.end(1)
    edits.append((start,end,'\n         RECT '+' '.join(f'{x:.4f}'for x in coords)+' ;\n      '))
    patches.append(dict(pin=pin.group(1),rect_dbu=[round(x*2000)for x in coords],original_bbox_um=[box.left,box.bottom,box.right,box.top]))
assert len(patches)==267
payload='set sram_landing_patches {\n'+''.join('  {'+p['pin']+' '+' '.join(map(str,p['rect_dbu']))+'}\n'for p in patches)+'}\n'
Path(OUTPUT).write_text(payload)
composite=text
for start,end,replacement in reversed(edits):composite=composite[:start]+replacement+composite[end:]
route_lef=Path(OUTPUT).with_name('bank-with-routing-landings.lef');route_lef.write_text(composite)
Path(RECEIPT).write_text(json.dumps(dict(passed=True,qualified=False,inputs={p:sha(p)for p in [GDS,LEF]},output=OUTPUT,output_sha256=sha(OUTPUT),patches=patches,all_original_connected_metal_covered=True,all_patches_clear_other_bank_m3_by_70nm=True,manufacturing_grid_um=.005,routing_lef=dict(path=str(route_lef),sha256=sha(route_lef),only_signal_m3_pin_geometry_changed=True,requires_all_1068_actual_top_level_patch_rectangles=True),scope='Composite route-only access view = unchanged bank plus charged top-level landings. Not a replacement standalone bank view. Every added rectangle must exist on its actual net in final ODB/DEF, RCX and GDS; full DRC and timing remain mandatory.'),indent=2)+'\n')
