"""Measure functional placement and connected empty tiles from a routed ODB."""
import argparse
import json
import os
from pathlib import Path
import subprocess


def audit(rows):
    boxes = {}
    active = []
    for line in rows.splitlines():
        if not line.startswith(('dbu\t', 'die\t', 'core\t', 'active\t')):
            continue
        label, *values = line.split('\t')
        values = tuple(map(int, values))
        if label == 'active':
            active.append(values)
        else:
            boxes[label] = values
    dbu, = boxes['dbu']
    assert active
    area = lambda b: (b[2]-b[0])*(b[3]-b[1])
    active_area = sum(map(area, active))
    left, bottom, right, top = boxes['core']
    tile = 10*dbu
    nx, ny = (right-left)//tile, (top-bottom)//tile
    assert nx and ny
    empty = {(x,y) for x in range(nx) for y in range(ny)}
    for x0,y0,x1,y1 in active:
        for x in range(max(0,(x0-left)//tile), min(nx,(x1-1-left)//tile+1)):
            for y in range(max(0,(y0-bottom)//tile), min(ny,(y1-1-bottom)//tile+1)):
                empty.discard((x,y))
    empty_count = len(empty)
    largest = 0
    while empty:
        todo = [empty.pop()]
        count = 0
        while todo:
            x,y = todo.pop()
            count += 1
            for adjacent in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if adjacent in empty:
                    empty.remove(adjacent)
                    todo.append(adjacent)
        largest = max(largest,count)
    return dict(active_area_um2=active_area/dbu**2,
                active_outline_ratio=active_area/area(boxes['die']),
                active_core_ratio=active_area/area(boxes['core']),
                grid_um=10, full_core_tiles=nx*ny, empty_core_tiles=empty_count,
                largest_connected_empty_region_um2=largest*100)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('odb',type=Path)
    parser.add_argument('report',type=Path)
    args=parser.parse_args()
    tcl=Path(__file__).with_suffix('.tcl')
    run=subprocess.run(['openroad','-no_init','-exit',str(tcl)],text=True,
                       env=dict(os.environ,COMPACT_ODB=str(args.odb.resolve())),
                       stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    run.check_returncode()
    args.report.write_text(json.dumps(audit(run.stdout),indent=2)+'\n')


if __name__=='__main__':
    main()
