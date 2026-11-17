from pathlib import Path
import re,json,collections
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v17-closure-r24-x16/flow/reports/nangate45/c-overlay-current/base')
out={}
for f in sorted(p.glob('congestion-*.rpt')):
 s=f.read_text();a=[tuple(map(int,m)) for m in re.findall(r'capacity:(\d+) usage:(\d+) congestion:(\d+)',s)]
 boxes=[tuple(map(float,m)) for m in re.findall(r'bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\)',s)]
 bins=collections.Counter((int((x+r)/400),int((y+t)/400)) for x,y,r,t in boxes)
 out[f.name]=dict(congested_edges=len(a),sum_overflow=sum(t for c,u,t in a),max_overflow=max(t for c,u,t in a),zero_capacity_edges=sum(c==0 for c,u,t in a),hot_200um_bins=[dict(x=b[0]*200,y=b[1]*200,count=v) for b,v in bins.most_common(12)])
print(json.dumps(out,indent=2))
(p.parent.parent.parent.parent.parent/'congestion-progression.json').write_text(json.dumps(out,indent=2))