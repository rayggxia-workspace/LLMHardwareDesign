"""Measure exact well mask geometry within 1 um of observed zero-width markers."""
import json
from pathlib import Path
import pya

db = pya.Layout()
db.read(GDS)
assert db.dbu == 0.0001
top = db.top_cell()
summary = []
for xy in COORDS.split(";"):
    cx, cy = (int(round(float(v) / db.dbu)) for v in xy.split(","))
    clip = pya.Box(cx - 10000, cy - 10000, cx + 10000, cy + 10000)
    layers = {}
    for layer in (1, 2, 3):
        index = db.find_layer(layer, 0)
        local = pya.Region(top.begin_shapes_rec_touching(index, clip)) & pya.Region(clip)
        local.move(-cx, -cy)
        layers[layer] = local.merged()
    well = (layers[2] | layers[3]).merged()
    summary.append({"marker_um": xy, "dbu_um": db.dbu,
                    "layers_relative": {number: str(geom) for number, geom in layers.items()},
                    "combined_well": str(well),
                    "combined_min_coherence": str(well.merged(True, 0)),
                    "combined_max_coherence": str(well.merged(False, 0))})
Path(OUT).write_text(json.dumps(summary, indent=2) + "\n")
