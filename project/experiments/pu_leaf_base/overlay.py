"""Write and independently check the straight research upper-metal coupons.

Inputs are exact metal10 BPin rectangles exported from the final routed ODB
and the corresponding native stream. Run under KLayout's Python interpreter.
"""
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path

import pya

root = Path(os.environ["PU_OVERLAY"])
config = json.loads((root / "inputs.json").read_text())
group = config["group"]
sizes = {"P": 32, "U": 128}
if group == "P":
    source, sink, handshake = "m_to_g_", "g_from_m_", "take"
else:
    source, sink, handshake = "n_to_e_", "e_direct_a_", "ready"

pins = defaultdict(list)
for line in (root / "m10-pins.tsv").read_text().splitlines():
    name, *coords = line.split()
    pins[name].append(tuple(map(int, coords)))

layer_map = {10: (29, 0), 11: (211, 0), 12: (213, 0), 110: (210, 0), 111: (212, 0)}
layout = pya.Layout()
layout.dbu = 0.0005
cell = layout.create_cell(f"PU_{group}_UPPER_COUPON")
native_file = next((root / "flow/results/nangate45").glob("*/base/6_final.gds"))
native = pya.Layout()
native.read(str(native_file))
layer = native.find_layer(*layer_map[10])
if layer is None:
    raise ValueError("native metal10 absent")
native_region = pya.Region(native.top_cell().begin_shapes_rec(layer))
native_region = native_region.transformed(pya.ICplxTrans(native.dbu / layout.dbu, 0, False, 0, 0))
native_region.merge()

half = 2000
expected = []
routes = {}


def landing(name):
    candidates = []
    for x0, y0, x1, y1 in pins[name]:
        x, y = (x0 + x1) // 2, (y0 + y1) // 2
        if x1 - x0 >= 2 * half and y1 - y0 >= 2 * half and (x - 190) % 8000 == (y - 140) % 8000 == 0:
            candidates.append((x, y))
    if len(candidates) != 1:
        raise ValueError(f"{name}: expected one research-grid M10 landing, got {candidates}")
    return candidates[0]


def insert(layer_number, coords, name):
    layer_info = layer_map[layer_number]
    shape = cell.shapes(layout.layer(*layer_info)).insert(pya.Box(*coords))
    shape.set_property(1, name)
    expected.append((layer_info, coords, name))


for suffix in [f"data[{i}]" for i in range(sizes[group])] + ["valid", handshake]:
    send, receive = source + suffix, sink + suffix
    if suffix == handshake:
        send, receive = receive, send
    a, b = landing(send), landing(receive)
    if a[0] != b[0] or a[1] == b[1]:
        raise ValueError(f"aligned vertical route unavailable: {send} -> {receive}: {a}, {b}")
    for x, y in (a, b):
        box = (x - half, y - half, x + half, y + half)
        if not (pya.Region(pya.Box(*box)) - native_region).is_empty():
            raise ValueError(f"via10 landing exceeds native M10: {send} -> {receive}: {(x,y)}")
        for layer_number in (110, 11, 111):
            insert(layer_number, box, suffix)
    insert(12, (a[0] - half, min(a[1], b[1]) - half, a[0] + half, max(a[1], b[1]) + half), suffix)
    routes[suffix] = {"driver": send, "sink": receive, "ends_dbu": [a, b],
                      "length_um": abs(a[1] - b[1]) * layout.dbu}

target = root / "upper-only.gds"
layout.write(str(target))
read = pya.Layout()
read.read(str(target))
observed = []
regions = {}
for number in (11, 12, 110, 111):
    pair = layer_map[number]
    index = read.find_layer(*pair)
    if index is None:
        raise ValueError(f"missing layer after GDS round-trip: {number}")
    region = pya.Region()
    for shape in read.top_cell().shapes(index).each():
        box = shape.box
        observed.append((pair, (box.left, box.bottom, box.right, box.top), shape.property(1)))
        region.insert(box)
    regions[number] = region.merged()
checks = {
    "exact_readback": sorted(expected) == sorted(observed),
    "only_upper_layers": {(item.layer, item.datatype) for item in read.layer_infos()} ==
                         {layer_map[n] for n in (11, 12, 110, 111)},
    "metal_width_spacing": all(regions[n].width_check(4000).is_empty()
                               and regions[n].space_check(4000).is_empty() for n in (11, 12)),
    "via_spacing": all(regions[n].space_check(4400).is_empty() for n in (110, 111)),
    "via10_covered": (regions[110] - native_region).is_empty() and (regions[110] - regions[11]).is_empty(),
    "via11_covered": (regions[111] - regions[11]).is_empty() and (regions[111] - regions[12]).is_empty(),
}
receipt = {"checks": checks, "routes": routes, "native": str(native_file),
           "overlay_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
(root / "overlay.json").write_text(json.dumps(receipt, indent=2))
if not all(checks.values()):
    raise RuntimeError(f"upper geometry failed: {checks}")
