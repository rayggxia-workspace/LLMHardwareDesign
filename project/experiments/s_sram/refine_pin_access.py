"""Conservative manufacturing-grid pin windows; run inside allocated KLayout.

Only PIN RECT coordinates change. Each new window is a nonempty subset of
its original window and actual same-layer GDS metal. No mask or circuit ECO.
"""
import hashlib, json, os, re
from decimal import Decimal
from pathlib import Path
import pya

assert os.environ.get('SLURM_JOB_ID')
gds, lef, output = map(Path, (GDS, LEF, OUTPUT))
assert not output.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
layout = pya.Layout(); layout.read(str(gds))
assert layout.dbu == .0005 and len(layout.top_cells()) == 1
layers = {f'metal{i}': 9 + 2*i for i in range(1, 11)}
# FreePDK45 drawing layer mapping: metal1=11, metal2=13, ...
regions = {}
text = lef.read_text(); changes = []; rows = []
rect = r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;'
for pin in re.finditer(r'(?ms)^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$', text):
    for part in re.finditer(r'(?s)LAYER\s+(\S+)\s*;(.*?)(?=\bLAYER\b|\bEND\b|\Z)', pin.group(2)):
        layer = part.group(1); assert layer in layers
        if layer not in regions:
            regions[layer] = pya.Region(layout.top_cell().begin_shapes_rec(layout.find_layer(layers[layer], 0))).merged()
        for m in re.finditer(rect, part.group(2)):
            values = [Decimal(x)*2000 for x in m.groups()]
            assert all(x == int(x) for x in values)
            old = list(map(int, values))
            new = [((x+9)//10)*10 if i < 2 else (x//10)*10 for i,x in enumerate(old)]
            assert new[0] < new[2] and new[1] < new[3]
            assert old[0] <= new[0] < new[2] <= old[2] and old[1] <= new[1] < new[3] <= old[3]
            assert (pya.Region(pya.Box(*new)) - regions[layer]).is_empty(), (pin.group(1), layer, old, new)
            start = pin.start(2)+part.start(2)+m.start(); end = pin.start(2)+part.start(2)+m.end()
            replacement = 'RECT '+' '.join(format(Decimal(x)/2000, '.4f') for x in new)+' ;'
            changes.append((start,end,replacement))
            rows.append(dict(pin=pin.group(1),layer=layer,original=old,access=new))
refined = text
for start,end,value in reversed(changes): refined = refined[:start]+value+refined[end:]
output.write_text(refined)
assert output.read_text() == refined
Path(RECEIPT).write_text(json.dumps(dict(passed=True,qualified=False,
    scope='Conservative pin access abstraction; actual routed access remains required',
    inputs={str(p):sha(p) for p in (gds,lef)},output=str(output),output_sha256=sha(output),
    manufacturing_grid_dbu=10,dbu_per_um=2000,only_pin_rectangles_changed=True,
    all_windows_nonempty_subsets_and_covered_by_actual_metal=True,rectangles=rows),indent=2)+'\n')
