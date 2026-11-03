"""Read captured actual router input; no routing, qualification or mutation."""
from pathlib import Path
import json

root=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control\work\YUZE-LU\162\continuation-proof-28\s-ready-composition-01\1391\upper-candidates')
for candidate in [1410,1430,1432,1433,1453]:
    path=root/str(candidate)/'route/trial-0/input.txt'
    if not path.exists():continue
    lines=path.read_text().splitlines();header=list(map(int,lines[0].split()))
    nx,ny,count=header[:3];rows=[]
    for line in lines[1:]:
        a=line.split();degree=int(a[1]);numbers=list(map(int,a[2:]));points=list(zip(numbers[:2*degree:2],numbers[1:2*degree:2]));assert len(points)==degree
        xs,ys=zip(*points);span=max(xs)-min(xs)+max(ys)-min(ys)
        rows.append(dict(name=a[0],degree=degree,xy_span=span,budget=numbers[2*degree]if len(numbers)>2*degree else None))
    assert len(rows)==count
    print(json.dumps(dict(candidate=candidate,grid=[nx,ny],total_nets=count,total_landings=sum(r['degree']for r in rows),high_fanout_nets=sum(r['degree']>16 for r in rows),high_fanout_span=sum(r['xy_span']for r in rows if r['degree']>16),total_xy_span=sum(r['xy_span']for r in rows),top_fanout=sorted(rows,key=lambda r:r['degree'],reverse=True)[:8]),ensure_ascii=False))
