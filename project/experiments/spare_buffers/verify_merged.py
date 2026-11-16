"""Read back the merged OASIS and verify assembly and translated M10 pads."""

import csv
import json
from collections import Counter
from pathlib import Path

import pya


out = Path(output_dir)
summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))


def read_table(filename):
    with (out / filename).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


layout = pya.Layout()
layout.read(str(out / "base-with-spares.oas"))
design = layout.top_cell()
names = summary["stream_cells"]
base = layout.cell(names["base"])
overlay = layout.cell(names["overlay"])
bank = layout.cell(names["bank"])
if design.name != names["top"]:
    raise ValueError("Unexpected merged top cell")
if {i.cell_index for i in design.each_inst()} != {base.cell_index(), overlay.cell_index()}:
    raise ValueError("The merged file does not contain the base and buffer overlay")


def instance_origins(cell):
    points = []
    for inst in cell.each_inst():
        for transform in inst.cell_inst.each_trans():
            points.append((transform.disp.x, transform.disp.y))
    return Counter(points)


expected_base = Counter(
    tuple(value * round(1 / (layout.dbu * 2000)) for value in view["translation_dbu"])
    for view in summary["base_instances"].values()
)
if instance_origins(base) != expected_base:
    raise ValueError("Block locations changed in OASIS read-back")
sites = read_table("banks.tsv")
expected_banks = Counter(
    tuple(round(float(site[key]) / layout.dbu) for key in ("origin_x_um", "origin_y_um"))
    for site in sites
)
if instance_origins(overlay) != expected_banks:
    raise ValueError("Bank locations changed in OASIS read-back")
if any(i.cell_index != bank.cell_index() for i in overlay.each_inst()):
    raise ValueError("Overlay references an unexpected bank master")

standalone = pya.Layout()
standalone.read(bank_gds)
original = standalone.cell("spare_bank")
if standalone.dbu != layout.dbu:
    raise ValueError("Unexpected bank unit conversion")
layer_pairs = {
    (standalone.get_info(index).layer, standalone.get_info(index).datatype)
    for index in standalone.layer_indexes()
}
for layer, datatype in layer_pairs - {(235, 0)}:
    before = pya.Region(original.begin_shapes_rec(standalone.find_layer(layer, datatype)))
    after = pya.Region(bank.begin_shapes_rec(layout.find_layer(layer, datatype)))
    if not (before ^ after).is_empty():
        raise ValueError(f"Bank geometry changed on {layer}/{datatype}")

metal10 = pya.Region(overlay.begin_shapes_rec(layout.find_layer(29, 0))).merged()
ports = read_table("m10-ports.tsv")
if len(ports) != 12 * summary["placed_banks"]:
    raise ValueError("Unexpected count in M10 table")
pad_region = pya.Region()
for port in ports:
    coords = [round(float(port[key]) / layout.dbu) for key in ("x0_um", "y0_um", "x1_um", "y1_um")]
    pad_region.insert(pya.Box(*coords))
    if port["pin"] in {"A", "Z"}:
        x, y = (round(float(port[key]) * 2000) for key in ("x_um", "y_um"))
        if (x - 190) % 400 or (y - 140) % 400:
            raise ValueError("Signal pad is off the PR271 fine V10 access lattice")
        side = round(2 / layout.dbu)
        if coords[2] - coords[0] != side or coords[3] - coords[1] != side:
            raise ValueError("Signal pad has unexpected size for a 2 um V10 cut")
if not (pad_region - metal10).is_empty():
    raise ValueError("Some listed M10 pads are missing in the merged layout")

receipt = {
    "base_instances_read_back": len(summary["base_instances"]),
    "banks_read_back": len(sites),
    "signal_port_rectangles_read_back": summary["m10_signal_ports"],
    "supply_port_rectangles_read_back": summary["m10_pg_shapes"],
    "bank_geometry_preserved": True,
    "pr271_v10_signal_centres_on_access_grid": True,
}
(out / "stream-verification.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt))
