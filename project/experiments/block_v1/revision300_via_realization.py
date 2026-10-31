"""Plan explicit via enclosures contained in the original conductor union.

Planning only: no database is changed and no DRC is waived. A plan still needs
an identity-clone control, actual ODB/full-DEF/connectivity audits, complete GDS
mask comparison and every final physical/numerical gate on the selected source.
"""
import copy
from decimal import Decimal
import hashlib
import re

from native_escape import parse


def dbu(value, units):
    scaled = Decimal(value) * units
    assert scaled == scaled.to_integral_value(), 'Non-integral database coordinate'
    return int(scaled)


def intervals(values):
    result = []
    for a, b in sorted(values):
        if result and a <= result[-1][1]:
            result[-1] = (result[-1][0], max(b, result[-1][1]))
        else:
            result.append((a, b))
    return result


def contains(box, rectangles):
    """Exact rectangle-union containment; bounding-box coverage is insufficient."""
    x, y, xx, yy = box
    assert x < xx and y < yy
    xs = sorted({x, xx} | {v for a, b, c, d in rectangles
                          for v in (a, c) if x < v < xx})
    return all(any(b <= y and d >= yy for b, d in intervals(
        (b, d) for a, b, c, d in rectangles if a <= lo and c >= hi))
        for lo, hi in zip(xs, xs[1:]))


def technology(text, units):
    widths = {}
    for m in re.finditer(r'(?ms)^LAYER (metal(?:[1-9]|10))\s*\n(.*?)^END \1\s*$', text):
        values = re.findall(r'^\s*WIDTH ([\d.]+)\s*;', m[2], re.M)
        assert len(values) == 1, 'Missing or ambiguous routing width'
        width = dbu(values[0], units)
        assert width > 0 and width % 2 == 0
        widths[m[1]] = width
    assert set(widths) == {'metal' + str(n) for n in range(1, 11)}
    vias = {}
    for m in re.finditer(r'(?ms)^VIA (via\d+_\d+) DEFAULT\s*\n(.*?)^END \1\s*$', text):
        layers = {}; layer = None
        for line in m[2].splitlines():
            match = re.match(r'\s*LAYER (\w+)\s*;', line)
            if match:
                layer = match[1]
            match = re.match(r'\s*RECT ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)\s*;', line)
            if match:
                assert layer and layer not in layers, 'Unsupported multi-rectangle via'
                layers[layer] = tuple(dbu(v, units) for v in match.groups())
        n = int(re.match(r'via(\d+)', m[1])[1])
        assert set(layers) == {'metal' + str(n), 'via' + str(n), 'metal' + str(n + 1)}
        vias[m[1]] = layers
    assert vias
    return widths, vias


def conductor_rectangles(paths, layer, widths, vias):
    result = []
    for p in paths:
        if p['via']:
            if layer in vias[p['via']]:
                x, y, _ = p['points'][0]
                a, b, c, d = vias[p['via']][layer]
                result.append((x+a, y+b, x+c, y+d))
        elif p['layer'] == layer:
            (x, y, e), (xx, yy, ee) = p['points']
            half = widths[layer] // 2
            ea = half if e is None else e
            eb = half if ee is None else ee
            if x == xx:
                result.append((x-half, min(y, yy)-(ea if y < yy else eb),
                               x+half, max(y, yy)+(eb if y < yy else ea)))
            else:
                result.append((min(x, xx)-(ea if x < xx else eb), y-half,
                               max(x, xx)+(eb if x < xx else ea), y+half))
    return result


def plan(report, records, tech_lef, units=2000):
    assert units == 2000, 'Only the audited Nangate45 database units are supported'
    widths, vias = technology(tech_lef, units)
    original = {n: parse(text) for n, text in records.items()}
    mods = {}; proposals = []; rejected = []
    for number, text in enumerate(report.split('violation type: ')[1:]):
        match = re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)', text)
        names = re.findall(r'net:([^\s]+)', text)
        if (text.splitlines()[0].strip() != 'Metal Spacing' or not match
                or not names or len(set(names)) != 1 or match[5] not in widths):
            rejected.append(dict(marker=number, reason='Unsupported marker or multiple nets'))
            continue
        net = names[0]; layer = match[5]
        if net not in original:
            rejected.append(dict(marker=number, net=net, reason='No exact source DEF record'))
            continue
        x, y, xx, yy = [dbu(v, units) for v in match.groups()[:4]]
        paths = original[net][1]
        union = conductor_rectangles(paths, layer, widths, vias)
        candidates = []
        for i, p in enumerate(paths):
            if not p['via'] or layer not in vias[p['via']]:
                continue
            cx, cy, _ = p['points'][0]
            local = mods.get((net, i), vias[p['via']])[layer]
            a, b, c, d = [local[j] + (cx if j % 2 == 0 else cy) for j in range(4)]
            options = []
            if c == x and b <= y and d >= yy: options.append((a, b, xx, d))
            if a == xx and b <= y and d >= yy: options.append((x, b, c, d))
            if d == y and a <= x and c >= xx: options.append((a, b, c, yy))
            if b == yy and a <= x and c >= xx: options.append((a, y, c, d))
            for box in options:
                if box[0] >= box[2] or box[1] >= box[3] or not contains(box, union):
                    continue
                area = (box[2]-box[0])*(box[3]-box[1])-(c-a)*(d-b)
                if area <= 0:
                    continue
                localbox = tuple(box[j]-(cx if j % 2 == 0 else cy) for j in range(4))
                candidates.append((area, i, localbox))
        if not candidates:
            rejected.append(dict(marker=number, net=net, layer=layer,
                                 reason='No enclosure extension contained in original same-net union'))
            continue
        area, i, box = min(candidates)
        p = paths[i]
        old = mods.setdefault((net, i), copy.deepcopy(vias[p['via']]))
        previous = old[layer]; old[layer] = box
        proposals.append(dict(marker=number, net=net, layer=layer, path=i,
                              via=p['via'], old_rectangle=previous,
                              new_rectangle=box, added_union_area=0))
    nets = {}
    for (net, i), layers in mods.items():
        n = int(re.match(r'via(\d+)', original[net][1][i]['via'])[1])
        assert layers['via'+str(n)] == vias[original[net][1][i]['via']]['via'+str(n)]
        nets.setdefault(net, dict(header=original[net][0], original_paths=original[net][1], changes=[]))['changes'].append(
            dict(path=i, original_via=original[net][1][i]['via'], rectangles=layers))
    return dict(source_report_sha256=hashlib.sha256(report.encode()).hexdigest(),
                tech_lef_sha256=hashlib.sha256(tech_lef.encode()).hexdigest(),
                units=units, routing_widths=widths, proposals=proposals,
                rejected=rejected, nets=nets, physical_qualified=False,
                scope='Planning only. Fixed wire paths, via centers/cuts, cells, pins and PG; added enclosure is inside original same-net union. All actual database and final gates remain required.')
