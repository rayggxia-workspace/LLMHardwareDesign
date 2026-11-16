"""Read streamed geometry back and trace every M10 port to its M1 pin."""

import csv
import json
from pathlib import Path

import pya


def table(name):
    with open(name, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file, delimiter="\t"))


layout = pya.Layout()
layout.read(input_gds)
top = layout.cell("spare_bank")
if top is None:
    raise ValueError("Missing spare_bank in streamed layout")

# Merge electrically touching shapes on each metal, and build a layer-by-layer
# graph through the actual cut polygons in the streamed output.
parents = []
metals = {}
for layer in range(1, 11):
    layer_id = layout.find_layer(9 + 2 * layer, 0)
    region = pya.Region(top.begin_shapes_rec(layer_id)).merged()
    polygons = []
    for polygon in region.each():
        node = len(parents)
        parents.append(node)
        polygons.append((node, polygon))
    metals[layer] = polygons


def root(node):
    while node != parents[node]:
        parents[node] = parents[parents[node]]
        node = parents[node]
    return node


def touching(layer, polygon):
    return [
        node for node, metal in metals[layer]
        if metal.bbox().overlaps(polygon.bbox()) and not (pya.Region(metal) & pya.Region(polygon)).is_empty()
    ]


cut_count = 0
for layer in range(1, 10):
    cut_id = layout.find_layer(10 + 2 * layer, 0)
    for cut in pya.Region(top.begin_shapes_rec(cut_id)).each():
        lower, upper = touching(layer, cut), touching(layer + 1, cut)
        if len(lower) != 1 or len(upper) != 1:
            raise ValueError(f"Unexpected cut connectivity at via{layer} {cut.bbox()}")
        parents[root(upper[0])] = root(lower[0])
        cut_count += 1


def probe(layer, x, y):
    scale = 1 / (2000 * layout.dbu)
    point = pya.Point(round(int(x) * scale), round(int(y) * scale))
    results = [root(node) for node, polygon in metals[layer] if polygon.inside(point)]
    if len(results) != 1:
        raise ValueError(f"Expected one M{layer} polygon at {x},{y}")
    return results[0]


signal_nodes = set()
power_nodes = {"VDD": set(), "VSS": set()}
signal_count = 0
for row in table(ports_tsv):
    top_node = probe(10, row["x_dbu"], row["y_dbu"])
    pin = row["pin"]
    if row["instance"] == "PG":
        power_nodes[pin].add(top_node)
        continue
    anchor = probe(1, row["anchor_x_dbu"], row["anchor_y_dbu"])
    if anchor != top_node or top_node in signal_nodes:
        raise ValueError(f"Open or short at {row['instance']}/{pin}")
    signal_nodes.add(top_node)
    signal_count += 1

for row in table(cells_tsv):
    x = int(row["x_dbu"]) + int(row["width_dbu"]) // 2
    y = int(row["y_dbu"])
    for supply, rail_y in (("VSS", y), ("VDD", y + int(row["height_dbu"]))):
        power_nodes[supply].add(probe(1, x, rail_y))
if any(len(nodes) != 1 or nodes & signal_nodes for nodes in power_nodes.values()):
    raise ValueError("Power rails open or shorted to signals")
if power_nodes["VDD"] & power_nodes["VSS"]:
    raise ValueError("VDD shorted to VSS")
if signal_count != 8:
    raise ValueError("Missing signal ports")
receipt = {"signal_ports_verified": signal_count, "power_nets_verified": 2, "via_shapes_checked": cut_count}
Path(receipt_file).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
