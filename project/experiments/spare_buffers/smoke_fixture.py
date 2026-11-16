"""Exercise a hierarchical 0.001 um input and an occupied M10 corridor."""

import json
from pathlib import Path

import pya


if mode == "create":
    layout = pya.Layout()
    layout.dbu = 0.001
    top = layout.create_cell("BASE")
    block = layout.create_cell("BLOCK")
    block.shapes(layout.layer(11, 0)).insert(pya.Box(0, 0, 50000, 260000))
    for x in (10000, 310000):
        top.insert(pya.CellInstArray(block.cell_index(), pya.Trans(x, 10000)))
    top.shapes(layout.layer(29, 0)).insert(pya.Box(118000, 0, 124000, 300000))
    layout.write("base.oas")
elif mode == "check":
    root = Path("result/merged")
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    if (summary["placed_buffers"], summary["geometry_blocked_sites"], summary["m10_signal_ports"]) != (16, 3, 32):
        raise ValueError("Unexpected placement or occupancy result")
    merged = pya.Layout()
    merged.read(str(root / "base-with-spares.oas"))
    old = merged.cell(summary["stream_cells"]["base"])
    for layer, boxes in (
        (11, [(10, 10, 60, 270), (310, 10, 360, 270)]),
        (29, [(118, 0, 124, 300)]),
    ):
        source_geometry = pya.Region()
        for box in boxes:
            source_geometry.insert(pya.Box(*(round(value / merged.dbu) for value in box)))
        readback = pya.Region(old.begin_shapes_rec(merged.find_layer(layer, 0)))
        if not (source_geometry ^ readback).is_empty():
            raise ValueError(f"Base geometry changed on GDS layer {layer}")
    print("Existing geometry preserved and occupied sites rejected")
else:
    raise ValueError("Unknown smoke fixture mode")
