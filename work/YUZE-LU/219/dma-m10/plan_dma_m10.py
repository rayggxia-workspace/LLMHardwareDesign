"""Allocate candidate native M10 pin sites on the audited DMA-v45 placement."""
import csv
import json
from pathlib import Path
import re
import sys

pins_path, geometry_path, landing_path = map(Path, sys.argv[1:])
geometry = {}
obstacles = []
for record in geometry_path.read_text().splitlines():
    key, *fields = record.split("\t")
    coordinates = tuple(int(value) for field in fields for value in field.split())
    if key == "obstacle":
        obstacles.append(coordinates)
    else:
        geometry[key] = coordinates

half, clearance, pitch = 2000, 4800, 12800
x0, y0, x1, y1 = geometry["core"]
xs = [x for x in geometry["x_grid"][::4] if x0 + pitch <= x <= x1 - pitch]
ys = [y for y in geometry["y_grid"][::4] if y0 + pitch <= y <= y1 - pitch]
blocked = {(i, j) for i, x in enumerate(xs) for j, y in enumerate(ys)
           if any(a-half-clearance < x < c+half+clearance
                  and b-half-clearance < y < d+half+clearance
                  for a, b, c, d in obstacles)}
with pins_path.open() as stream:
    pins = list(csv.DictReader(stream, delimiter="\t"))
die = geometry["die"]
requests = []
for record in pins:
    shapes = re.findall(r"\{(metal[56]) [56] (\d+) (\d+) (\d+) (\d+)\}",
                        record["placed_bpin_shapes"])
    if len(shapes) != 1:
        raise ValueError("expected one source BPin for " + record["logical_pin"])
    _, a, b, c, d = shapes[0]
    a, b, c, d = map(int, (a, b, c, d))
    x, y = (a+c)//2, (b+d)//2
    if a == die[0]:
        side, x, order = "left", x0+20*pitch, y
    elif b == die[1]:
        side, y, order = "bottom", y0+20*pitch, x
    elif c == die[2]:
        side, x, order = "right", x1-20*pitch, y
    elif d == die[3]:
        side, y, order = "top", y1-20*pitch, x
    else:
        raise ValueError("source BPin is away from the DMA die boundary")
    requests.append((side, order, record["logical_pin"], record["direction"], x, y))

def site(x, y):
    i = min(range(len(xs)), key=lambda k: abs(xs[k] - x))
    j = min(range(len(ys)), key=lambda k: abs(ys[k] - y))
    for radius in range(80):
        free = []
        for u in range(max(0, i-radius), min(len(xs), i+radius+1)):
            span = radius - abs(u-i)
            for v in {j-span, j+span}:
                if 0 <= v < len(ys) and (u, v) not in blocked:
                    free.append((abs(xs[u]-x)+abs(ys[v]-y), u, v))
        if free:
            _, u, v = min(free)
            blocked.add((u, v))
            return xs[u], ys[v]
    raise ValueError("no M10 landing site near the original DMA interface")

with landing_path.open("w") as stream:
    for _, _, name, role, x, y in sorted(requests):
        a, b = site(x, y)
        print(name, role, a-half, b-half, a+half, b+half, sep="\t", file=stream)
print(json.dumps({"landings": len(requests), "layer": "metal10", "pitch_dbu": pitch,
                  "routing_status": "unverified", "obstacles": len(obstacles)}))
