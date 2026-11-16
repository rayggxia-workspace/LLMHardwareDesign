"""Build sparse local M11/M12/V11 candidates using historical hotspots and fixed pins."""
from collections import Counter
from decimal import Decimal
import csv
import json
from pathlib import Path
import sys


graph, spec_file, historical, output, metadata = map(Path, sys.argv[1:])
spec = json.loads(spec_file.read_bytes())
tech = spec['technology']
assert len(spec['nets']) == 1184 and tech['pitch'] == 21 * tech['access_pitch']
assert not spec['obstacles']
ox, oy = tech['origin']
step = tech['access_pitch']
pitch = tech['pitch'] // step
bins = Counter()
pin_locations = []
with graph.open() as stream:
    xmin, ymin, xmax, ymax, nets = map(int, next(stream).split())
    assert nets == 1184
    for i in range(nets):
        n, pins, windows = map(int, next(stream).split())
        assert n == i
        pin_locations.extend(tuple(map(int, next(stream).split())) for _ in range(pins))
        for _ in range(windows): next(stream)
assert len(pin_locations) == 2858
with historical.open() as stream:
    for row in csv.DictReader(stream, delimiter='\t'):
        x = row['observed_region_x_um']; y = row['observed_region_y_um']
        if row['cause'] != 'channel' or not x or not y:
            continue
        x = int((Decimal(x)*2000-ox)/step)
        y = int((Decimal(y)*2000-oy)/step)
        bins[x,y] += 1


def tracks(lo, hi, samples):
    primary = list(range(lo, hi+1, pitch))
    counts = Counter(v for v in samples if lo < v < hi)
    chosen = {}
    target = min(12, len(primary)-1)
    # Give nearby fixed pin coordinates priority, spread the remaining options across the window.
    for axis, weight in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if len(chosen) >= target//2: break
        if 3 <= axis % pitch <= pitch-3:
            chosen.setdefault(axis//pitch, axis)
    anchors = [(lo+i*pitch)//pitch for i in range(len(primary)-1)]
    order = []
    while len(order) < len(anchors):
        unpicked = [a for a in anchors if a not in order]
        order.append(max(unpicked, key=lambda a: (min(abs(a-b) for b in order+[anchors[0]-1,anchors[-1]+1]),-a)))
    for interval in order:
        if len(chosen) == target: break
        chosen.setdefault(interval, interval*pitch+pitch//2)
    return sorted(set(primary).union(chosen.values())), sorted(chosen.values())


edges = set()
windows = []
for (cx,cy), nfail in sorted(bins.items(), key=lambda kv:(-kv[1],kv[0]))[:8]:
    radius = 760
    l = (max(xmin,cx-radius)+pitch-1)//pitch*pitch
    b = (max(ymin,cy-radius)+pitch-1)//pitch*pitch
    r = min(xmax,cx+radius)//pitch*pitch
    t = min(ymax,cy+radius)//pitch*pitch
    assert r-l >= pitch and t-b >= pitch
    assert all(r<w['lattice_bounds'][0] or l>w['lattice_bounds'][2] or
               t<w['lattice_bounds'][1] or b>w['lattice_bounds'][3] for w in windows)
    nearby = [(x,y) for x,y in pin_locations if l<=x<=r and b<=y<=t]
    xs, off_x = tracks(l,r,[x for x,_ in nearby])
    ys, off_y = tracks(b,t,[y for _,y in nearby])
    before = len(edges)
    for y in ys:
        edges.update((x,y,0,z,y,0) for x,z in zip(xs,xs[1:]) if y%pitch or x%pitch or z%pitch)
    for x in xs:
        edges.update((x,y,1,x,z,1) for y,z in zip(ys,ys[1:]) if x%pitch or y%pitch or z%pitch)
    edges.update((x,y,0,x,y,1) for x in xs for y in ys if x%pitch or y%pitch)
    windows.append({'lattice_bounds':[l,b,r,t],'center_um':[(cx*step+ox)/2000,(cy*step+oy)/2000],
                    'historical_channel_failures':nfail,'fixed_landing_count':len(nearby),
                    'M11_extra_y_dbu':[v*step+oy for v in off_y], 'M12_extra_x_dbu':[v*step+ox for v in off_x],
                    'arcs':len(edges)-before})
assert len(windows)==8
with output.open('x') as stream:
    for edge in sorted(edges): print(*edge,file=stream)
with metadata.open('x') as stream:
    json.dump({'regions':windows,'access_step_dbu':step,'origin_dbu':[ox,oy],
               'wire_arcs':sum(e[2]==e[5] for e in edges),'via11_arcs':sum(e[2]!=e[5] for e in edges)},
              stream,sort_keys=True,indent=2)
    stream.write('\n')
