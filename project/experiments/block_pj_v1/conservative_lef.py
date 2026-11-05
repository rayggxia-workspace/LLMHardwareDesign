"""Keep true terminal metal as pin geometry and bound dense lower-layer OBS.

Every moved rectangle is an intersection between an existing LEF M8/M9/M10
obstruction and a real same-net ODB wire rectangle within the landing window.
The union of metal geometries stays the same.
"""
from collections import defaultdict
from decimal import Decimal
import re
import sys
from pathlib import Path

source, routes, dest = (Path(p) for p in sys.argv[1:])
text = source.read_text()
head, mark, obs = text.partition('\n  OBS\n')
assert mark and obs
w, h = re.search(r'(?m)^  SIZE (\S+) BY (\S+) ;', head).groups()
layers = re.split(r'(?m)^    LAYER (\S+) ;\n', obs)
assert layers[0] == ''

dbu = 2000
grid = 16000
terminal = defaultdict(list)
for line in routes.read_text().splitlines():
    pin, layer, box = line.split('\t')
    box = tuple(map(int, box.split()))
    for x in range(box[0] // grid, box[2] // grid + 1):
        for y in range(box[1] // grid, box[3] // grid + 1):
            terminal[layer, x, y].append((pin, box))


def db_coord(value):
    scaled = Decimal(value) * dbu
    assert scaled == int(scaled)
    return int(scaled)


def rectangle(box):
    return '      RECT ' + ' '.join(str(Decimal(x) / dbu) for x in box) + ' ;\n'


def subtract(a, b):
    x0, y0, x1, y1 = a
    l, btm, r, t = b
    return [q for q in ((x0, y0, l, y1), (r, y0, x1, y1),
                        (l, y0, r, btm), (l, t, r, y1))
            if q[0] < q[2] and q[1] < q[3]]


moved = defaultdict(list)
changes = {}
for i in range(1, len(layers), 2):
    name, geom = layers[i:i + 2]
    if name in {'metal8', 'metal9', 'metal10'}:
        obs_lines = []
        for line in geom.splitlines(keepends=True):
            tokens = line.split()
            if not tokens or tokens[0] != 'RECT':
                obs_lines.append(line)
                continue
            box = tuple(db_coord(v) for v in tokens[1:5])
            candidates = set()
            for x in range(box[0] // grid, box[2] // grid + 1):
                for y in range(box[1] // grid, box[3] // grid + 1):
                    candidates.update(terminal.get((name, x, y), []))
            remaining = [box]
            for pin, part in sorted(candidates):
                rest = []
                for a in remaining:
                    intersection = (max(a[0], part[0]), max(a[1], part[1]),
                                    min(a[2], part[2]), min(a[3], part[3]))
                    if intersection[0] >= intersection[2] or intersection[1] >= intersection[3]:
                        rest.append(a)
                        continue
                    moved[pin].append((name, intersection))
                    rest.extend(subtract(a, intersection))
                remaining = rest
            obs_lines.extend(rectangle(r) for r in remaining)
        layers[i + 1] = ''.join(obs_lines)
    if name not in {f'metal{x}' for x in range(1, 7)}:
        continue
    box = [0, 0, db_coord(w), db_coord(h)]
    count = 0
    for line in geom.splitlines():
        p = line.split()
        if not p:
            continue
        assert p[0] == 'RECT' and p[-1] == ';' and len(p) == 6, line
        x0, y0, x1, y1 = map(db_coord, p[1:5])
        box = [min(box[0], x0), min(box[1], y0), max(box[2], x1), max(box[3], y1)]
        count += 1
    changes[name] = count
    layers[i + 1] = rectangle(box)
assert len(changes) == 6 and moved


def expand_pin(match):
    name, body = match.groups()
    boxes = moved.pop(name, [])
    if not boxes:
        return match.group()
    terminal_layer = '      LAYER metal10 ;\n'
    assert body.count(terminal_layer) == 1, name
    landing = terminal_layer + ''.join(rectangle(b) for layer, b in boxes if layer == 'metal10')
    for approach_layer in ('metal9', 'metal8'):
        approach = [rectangle(b) for layer, b in boxes if layer == approach_layer]
        if approach:
            landing = f'      LAYER {approach_layer} ;\n' + ''.join(approach) + landing
    return f'  PIN {name}\n' + body.replace(terminal_layer, landing) + f'  END {name}\n'


print(f'{source}: covered lower-layer rectangles {changes}; same-net M8/M9/M10 reclassification on {len(moved)} pins')
head = re.sub(r'^  PIN (\S+)\n(.*?)^  END \1\n', expand_pin, head, flags=re.M | re.S)
assert not moved, list(moved)[:8]
with dest.open('x') as stream:
    stream.write(head + mark)
    for name, geom in zip(layers[1::2], layers[2::2]):
        stream.write(f'    LAYER {name} ;\n{geom}')
