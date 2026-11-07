"""Export native upper cut shapes to the parent routing abstract."""
from pathlib import Path

import pya


layout = pya.Layout()
layout.read(GDS)
leaf = layout.top_cell()
lines = []
for name, gds_layer in (("via6", 22), ("via7", 24), ("via8", 26), ("via9", 28)):
    layer = layout.find_layer(gds_layer, 0)
    if layer is None:
        continue
    region = pya.Region(leaf.begin_shapes_rec(layer))
    boxes = sorted({(b.left, b.bottom, b.right, b.top) for b in (shape.bbox() for shape in region.each())})
    if boxes:
        lines.append(f"    LAYER {name} ;")
        for box in boxes:
            coordinates = " ".join(f"{value * layout.dbu:.5f}" for value in box)
            lines.append(f"     RECT {coordinates} ;")
Path(CUTS).write_text("\n".join(lines) + "\n")
