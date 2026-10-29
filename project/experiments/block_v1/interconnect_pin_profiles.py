"""Reproducible Manhattan lower bounds from accepted internal M10 pins.

No concurrent routing, legal repeater site, detour or coupling claim is made.
Both macros are R0, with a declared80um gap. Four adjacent placements are
compared and the smallest maximum pin-to-pin distance is selected per pair.
"""
import argparse
import json
from pathlib import Path
from statistics import median

from interconnect_spef import paired_links, sha


def profiles(root, gap=80.):
    base = root / 'work/YUZE-LU/121/delivery-300mhz'
    pins, inputs = {}, {}
    for kind in ('m', 't', 's'):
        path = base / kind.upper() / ('pins.json' if kind == 's' else 'interface/actual-escape.json')
        data = json.loads(path.read_text())
        if kind == 's':
            size = [1610., 1610.]
            pins[kind] = {r['pin']: [(r['box_um'][i] + r['box_um'][i+2])/2 for i in (0,1)]
                          for r in data['pins']}
            assert all(r['layer']=='metal10' for r in data['pins'])
        else:
            scale = data['dbu_per_um']; box = data['macro_box_dbu']
            size = [(box[i+2]-box[i])/scale for i in (0,1)]
            pins[kind] = {r['net']: [(r['source_m10_dbu'][i]-box[i])/scale for i in (0,1)]
                          for r in data['ports']}
        assert all(0 <= xy[i] <= size[i] for xy in pins[kind].values() for i in (0,1))
        inputs[kind] = dict(path=path.relative_to(root).as_posix(), sha256=sha(path), die_um=size)
    pairs = {}
    for pair in ('mt', 'ts'):
        left,right=pair; lw,lh=inputs[left]['die_um']; rw,rh=inputs[right]['die_um']
        orientations = {}
        for direction,offset in [('east',(lw+gap,0)),('west',(-rw-gap,0)),
                                 ('north',(0,lh+gap)),('south',(0,-rh-gap))]:
            rows=[]
            for link in paired_links(*pair):
                coords=[]
                for side,port in (link['source'],link['sink']):
                    kind=left if side=='left' else right
                    xy=pins[kind][port]
                    coords.append([xy[i]+(offset[i] if side=='right' else 0) for i in (0,1)])
                a,b=coords
                rows.append(dict(**link,source_xy_um=a,sink_xy_um=b,
                                 manhattan_min_um=round(sum(abs(a[i]-b[i])for i in (0,1)),6)))
            lengths=[r['manhattan_min_um']for r in rows]
            orientations[direction]=dict(min_um=min(lengths),median_um=median(lengths),max_um=max(lengths),rows=rows)
        best=min(orientations,key=lambda x:orientations[x]['max_um'])
        pairs[pair]=dict(placements=orientations,selected_placement=best,
                        selected_lengths_um={r['id']:r['manhattan_min_um']for r in orientations[best]['rows']})
    return dict(schema='actual-pin-manhattan-lower-bounds/1',inputs=inputs,gap_um=gap,
                rotations='R0 only',simultaneous_routing_qualified=False,
                scope='Actual accepted internal M10 pins; shortest Manhattan distances only. No detours, repeater sites, congestion or coupling qualification.',pairs=pairs)


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('root',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--summary',action='store_true',help='Keep selected per-bit lengths and all placement statistics; omit duplicate coordinate rows')
    a=p.parse_args();result=profiles(a.root)
    if a.summary:
        for pair in result['pairs'].values():
            for placement in pair['placements'].values():placement.pop('rows')
        result['omitted_placement_coordinate_rows']=True
    a.output.write_text(json.dumps(result,indent=2)+'\n')
