"""Necessary vertex-cut analysis of captured router inputs; no routing.

Every net with a terminal strictly inside the rectangle and one outside it
must occupy a distinct boundary vertex. Two layers supply2*(2*w+2*h-4)
boundary vertices; fixed M11 terminals belonging to non-crossing nets cannot
be used. This is only a failure test for the declared discrete routing scene.
"""
from pathlib import Path
import numpy as np,json,time

root=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control\work\YUZE-LU\162\continuation-proof-28\s-ready-composition-01\1391\upper-candidates')
for case in [1430,1432,1433]:
    path=root/str(case)/'route/trial-0/input.txt';lines=path.read_text().splitlines();nx,ny,count=map(int,lines[0].split()[:3]);points=[];degrees=[]
    for i,line in enumerate(lines[1:]):
        v=line.split();n=int(v[1]);a=list(map(int,v[2:2+2*n]));points.extend((x,y,i)for x,y in zip(a[::2],a[1::2]));degrees.append(n)
    a=np.asarray(points);x,y,net=a.T;degrees=np.asarray(degrees);best=(0,None);checks=0
    centres={(int(xx)//16*16,int(yy)//16*16)for xx,yy,_ in points}
    for w,h in [(24,24),(32,32),(64,64),(128,128),(256,256),(512,512),(128,32),(32,128),(256,64),(64,256)]:
        for cx,cy in centres:
            x0=max(4,min(cx-w//2,nx-4-w));y0=max(4,min(cy-h//2,ny-4-h));x1=x0+w-1;y1=y0+h-1
            # Boundary terminals cannot count as strictly interior demand.
            inside=(x>x0)&(x<x1)&(y>y0)&(y<y1)
            interior=np.bincount(net[inside],minlength=count)
            # An outside terminal is beyond the inner boundary, not on it.
            outside=(x<x0)|(x>x1)|(y<y0)|(y>y1)
            exterior=np.bincount(net[outside],minlength=count)
            crossing=(interior>0)&(exterior>0)
            demand=int(crossing.sum())
            boundary=(((x==x0)|(x==x1))&(y>=y0)&(y<=y1))|(((y==y0)|(y==y1))&(x>=x0)&(x<=x1))
            occupied_non_crossing=int((~crossing[net[boundary]]).sum())
            capacity=2*(2*w+2*h-4)-occupied_non_crossing
            ratio=demand/capacity;checks+=1
            if ratio>best[0]:best=(ratio,dict(rectangle=[x0,y0,x1,y1],crossing_nets=demand,boundary_vertex_capacity=capacity,fixed_non_crossing_landings=occupied_non_crossing))
    print(json.dumps(dict(candidate=case,checked_rectangles=checks,max_ratio=best[0],worst=best[1],necessary_failure=best[0]>1,scope='Failure-only discrete grid cut, never a routability/physical acceptance proof.')))
