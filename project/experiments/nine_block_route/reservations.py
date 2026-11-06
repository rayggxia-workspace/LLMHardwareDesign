"""Validate rectangular reservations for an unimplemented parent floorplan."""
from itertools import combinations
import json
from pathlib import Path
import sys

path=Path(sys.argv[1])
spec=json.loads(path.read_text())
positions=spec["positions_um"]
sizes=spec["sizes_um"]
width,height=spec["die_um"]
gap=spec["clearance_setting_um"]
bounds={}
for name,(x,y) in positions.items():
    w,h=sizes[name[0]]
    bounds[name]=(x,y,x+w,y+h)
reservations={}
if "--local" in sys.argv[2:]:
    # Shorten and localize the reservations next to the compact C/U pair.
    for name,(x,y,x1,y1) in bounds.items():
        reservations[f"{name}.local_control"]=(x,y-28,x+384,y-8)
        reservations[f"{name}.transport"]=(x+400,y-28,x+1008,y-8)
        reservations[f"{name}.side_access"]=(x-48,y+32,x-8,y1-32)
        reservations[f"{name}.clock"]=(x,y-44,x1,y-32)
        reservations[f"{name}.power"]=(x,y-64,x1,y-48)
else:
    for name,(x,y,x1,y1) in bounds.items():
        reservations[f"{name}.local_control"]=(x,y-72,x+384,y-32)
        reservations[f"{name}.transport"]=(x+400,y-72,x+1008,y-32)
        reservations[f"{name}.side_access"]=(x-48,y+32,x-8,y1-32)
    # Each occupied row gets dedicated native PG/clock study stripes in the
    # lower gap. These are reservation polygons, with no claimed tracks or vias.
    for y in sorted({v[1] for v in bounds.values()}):
        reservations[f"row{y}.clock"]=(gap,y-100,width-gap,y-88)
        reservations[f"row{y}.power"]=(gap,y-124,width-gap,y-108)
all_boxes={**bounds,**reservations}
for name,(a,b,c,d) in all_boxes.items():
    if not (0<=a<c<=width and 0<=b<d<=height):
        raise ValueError(f"out of boundary: {name}")
for (name,a),(other,b) in combinations(all_boxes.items(),2):
    if max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3]):
        raise ValueError(f"overlap: {name} and {other}")
path.with_name("reservations.json").write_text(json.dumps(dict(
    blocks=bounds, reservations=reservations, actual_parent_rtl=False,
    actual_pg_clock=False, positions_only=True),indent=2))
print(len(bounds),len(reservations),"non-overlapping rectangles")
