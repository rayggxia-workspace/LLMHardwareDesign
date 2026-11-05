"""Produce a mask-equivalent GDS for a full-deck performance comparison."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import pya

source, output, receipt = map(Path, (SOURCE, OUTPUT, RECEIPT))
assert not output.exists() and not receipt.exists()
def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

raw_sha = sha(source)
raw = pya.Layout()
raw.read(str(source))
derived = pya.Layout()
derived.read(str(source))
assert raw.dbu == derived.dbu == 0.0001
# FEOL well and implant layers are already combined by the native deck.
# Change their representation only. The manufactured masks must XOR to zero.
mask_layers = {2, 3, 4, 5}
raw_layers = {raw.get_info(i).to_s() for i in raw.layer_indices()}
for n in sorted(mask_layers):
    idx = derived.find_layer(n, 0)
    top = derived.top_cell()
    region = pya.Region(top.begin_shapes_rec(idx)).merged()
    assert not region.is_empty()
    for cell in derived.each_cell():
        layer = cell.shapes(idx)
        for shape in list(layer.each()):
            if not shape.is_text():
                layer.erase(shape)
    top.shapes(idx).insert(region)
    print(f'MASK {n} polygons={region.count()}', flush=True)
derived.write(str(output))
after = pya.Layout()
after.read(str(output))
assert after.dbu == raw.dbu
assert {c.name for c in raw.each_cell()} == {c.name for c in after.each_cell()}
assert {after.get_info(i).to_s() for i in after.layer_indices()} == raw_layers
assert raw.top_cell().name == after.top_cell().name

def instances(cell):
    return Counter((inst.cell.name, trans.mag, trans.angle, trans.is_mirror(), trans.disp.x, trans.disp.y)
                   for inst in cell.each_inst() for trans in inst.cell_inst.each_cplx_trans())

def shapes(cell, idx, labels):
    return Counter(shape.to_s() for shape in cell.shapes(idx).each()
                   if not labels or shape.is_text())

for cell in raw.each_cell():
    copy = after.cell(cell.name)
    assert instances(cell) == instances(copy), cell.name
    for idx in raw.layer_indices():
        info = raw.get_info(idx)
        labels = info.layer in mask_layers and info.datatype == 0
        dest = after.find_layer(info.layer, info.datatype)
        assert shapes(cell, idx, labels) == shapes(copy, dest, labels), (cell.name, info.to_s())

for n in sorted(mask_layers):
    raw_mask = pya.Region(raw.top_cell().begin_shapes_rec(raw.find_layer(n, 0))).merged()
    new_mask = pya.Region(after.top_cell().begin_shapes_rec(after.find_layer(n, 0))).merged()
    assert (raw_mask ^ new_mask).is_empty(), n
    assert not (raw_mask ^ new_mask.transformed(pya.Trans(1, 0))).is_empty(), n
assert sha(source) == raw_sha
receipt.write_text(json.dumps(dict(source=str(source), source_sha256=raw_sha, output_sha256=sha(output),
                                  layers=sorted(mask_layers), all_selected_mask_xors_empty=True,
                                  one_dbu_shift_rejected=True, other_shapes_labels_and_instances_exact=True),
                              indent=2) + '\n')
