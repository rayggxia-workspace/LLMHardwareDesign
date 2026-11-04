from pathlib import Path
from bisect import bisect_left, bisect_right
from collections import defaultdict, Counter
import hashlib, json, time

root=Path(__file__).parent/'control162-static795'
raw=(root/'input.txt').read_bytes(); lines=raw.decode().splitlines()
nx,ny,count,seed,rounds,weight,locked,*flags=map(int,lines[0].split())
nets=[]; rows=defaultdict(list); cols=defaultdict(list)
for line in lines[1:]:
    p=line.split(); k=int(p[1]); pts=[tuple(map(int,p[2+2*j:4+2*j])) for j in range(k)]
    nets.append((p[0],pts))
    for x,y in pts: rows[y].append(x); cols[x].append(y)
for seq in list(rows.values())+list(cols.values()): seq.sort()

def blocked(x,y,xx,yy,own):
    if (x,y)==(xx,yy): return False
    if y==yy:
        seq=rows[y]; a,b=sorted((x,xx)); total=bisect_right(seq,b)-bisect_left(seq,a)
        total-=int(x in seq)
        total-=sum(y==py and a<=px<=b and (px,py)!=(x,y) for px,py in own)
    else:
        seq=cols[x]; a,b=sorted((y,yy)); total=bisect_right(seq,b)-bisect_left(seq,a)
        total-=int(y in seq)
        total-=sum(x==px and a<=py<=b and (px,py)!=(x,y) for px,py in own)
    return total>0

def possible(pts):
    (tx,ty),(sx,sy)=pts
    for orient in range(2):
        a,b=(sy,ty) if orient else (sx,tx); middle=(a+b)//2; mids=[]
        for m in [middle,(3*a+b)//4,(a+3*b)//4,a,b]+[middle+sgn*d for d in range(1,17) for sgn in (-1,1)]+[m for d in (2,4,8,16,32,64) for m in (min(a,b)-d,max(a,b)+d)]:
            if 4<=m<(ny if orient else nx)-4 and m not in mids: mids.append(m)
        for m in mids:
            points=[(sx,m),(tx,m),(tx,ty)] if orient else [(m,sy),(m,ty),(tx,ty)]
            for mask in ((5,2,0,7,1,3,4,6) if orient else (2,5,0,7,1,3,4,6)):
                x,y,l=sx,sy,0; valid=True
                for j,(xx,yy) in enumerate(points):
                    ll=(mask>>j)&1
                    if ll!=l:
                        if (x+y)%2 or (ll==0 and (x in rows[y]) and (x,y) not in pts): valid=False; break
                        l=ll
                        if not l and (x,y)==(tx,ty): return (orient,m,mask)
                    reached=False
                    if l==0:
                        if (y==yy==ty and min(x,xx)<=tx<=max(x,xx)) or (x==xx==tx and min(y,yy)<=ty<=max(y,yy)):
                            xx,yy=tx,ty; reached=True
                        if blocked(x,y,xx,yy,pts): valid=False; break
                    x,y=xx,yy
                    if reached: return (orient,m,mask)
                if valid and l and (x+y)%2==0: return (orient,m,mask)
    return None

started=time.time(); counts=Counter(); samples={}; failed=[]; found=[]
for i,(name,pts) in enumerate(nets):
    if i<locked or len(pts)!=2: continue
    parity=''.join(str((x+y)%2) for x,y in pts)
    ans=possible(pts); key=parity+('_eligible' if ans else '_no_pattern'); counts[key]+=1
    if len(samples.setdefault(key,[]))<8: samples[key].append(dict(name=name,points=pts,witness=ans))
    (found if ans else failed).append(name)
report=dict(schema='static-geometric-potential-v1',scope='Static M11 landing reservations and checkerboard vias only. Ignores occupancy/history and the production 65536 vertex-test budget. Eligibility is an upper bound on this geometric prepass, not a global routing feasibility result.',input_sha256=hashlib.sha256(raw).hexdigest(),program_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),nx=nx,ny=ny,locked=locked,pair_count=len(found)+len(failed),eligible=len(found),no_pattern=len(failed),counts=dict(counts),samples=samples,elapsed_seconds=time.time()-started)
(root/'receipt.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
(root/'eligible.json').write_bytes((json.dumps(found)+'\n').encode()); (root/'no-pattern.json').write_bytes((json.dumps(failed)+'\n').encode())
print(json.dumps({k:v for k,v in report.items() if k!='samples'}))
