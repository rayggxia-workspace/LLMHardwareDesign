"""Prove every real M10 mother terminal rectangle exists in exported native GDS."""
import hashlib, json
from pathlib import Path
import pya

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

layout = pya.Layout()
layout.read(str(GDS))
roots = layout.top_cells()
assert len(roots) == 1 and roots[0].name == 'mother_control_64'
layer = layout.find_layer(29, 0)
assert layer is not None
metal = pya.Region(roots[0].begin_shapes_rec(layer))
metal.merge()
names = set()
for line in Path(PINS).read_text().splitlines():
    name, native_layer, *coords = line.split('\t')
    assert native_layer == 'metal10' and len(coords) == 4 and name not in names
    names.add(name)
    raw = list(map(int, coords))
    assert raw[2]-raw[0] == raw[3]-raw[1] == 4000
    scaled = [round(v / 2000 / layout.dbu) for v in raw]
    box = pya.Box(*scaled)
    assert (pya.Region(box)-metal).is_empty(), name
assert len(names) == 2446
bounds = roots[0].bbox()
control = pya.Box(bounds.right+10000,bounds.top+10000,bounds.right+12000,bounds.top+12000)
assert not (pya.Region(control)-metal).is_empty()
Path(RECEIPT).write_text(json.dumps(dict(schema='mother-native-gds-pin-proof/1',passed=True,
    count=len(names),metal_layer=[29,0],odb_units_per_um=2000,gds_dbu_um=layout.dbu,
    gds_sha256=sha(GDS),pins_sha256=sha(PINS),outside_negative_control=True,
    scope='All native M10 terminal rectangles covered by actual GDS copper; no simultaneous M11/M12 escape claim'),indent=2)+'\n')