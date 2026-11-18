import json
from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
a=r/'audit/U-v8-postroute-h02-e10-independent-v1/original-geometry.tsv'
b=r/'cu/runs/U-v8-postroute-h02-e10/flow/results/nangate45/u-overlay-current/base/geometry-after.tsv'
def separate(p):
 rows=set(p.read_text().splitlines());pg={s for s in rows if s.startswith(('PIN\tVDD\t','PIN\tVSS\t'))};return rows-pg,pg
x,px=separate(a);y,py=separate(b)
o=dict(signal_die_macro_geometry_equal=x==y,other_removed=sorted(x-y),other_added=sorted(y-x),power_rectangles_removed=len(px-py),power_rectangles_added=len(py-px))
(r/'audit/U-original-signal-geometry.json').write_text(json.dumps(o,indent=2));print(json.dumps(o,indent=2))
