from pathlib import Path
import runpy,json,hashlib,time
ns=runpy.run_path(str(Path(__file__).with_name('control162-static795.py')))
root=ns['root']; nets=ns['nets']; own_index={name:(i,pts) for i,(name,pts) in enumerate(nets)}
reservations={p:i for i,(_,pts) in enumerate(nets) for p in pts}
count=vertices=vias=edges=0; started=time.time()
for name in json.loads((root/'eligible.json').read_bytes()):
    i,pts=own_index[name]; target,start=pts; orientation,mid,mask=ns['possible'](pts)
    x,y=start;l=0;done=False
    points=[(x,mid),(target[0],mid),target] if orientation else [(mid,y),(mid,target[1]),target]
    def check(xx,yy,ll):
        global x,y,l,done,vertices,vias,edges
        assert 4<=xx<ns['nx']-4 and 4<=yy<ns['ny']-4
        assert ll==1 or reservations.get((xx,yy),i)==i
        if ll!=l:
            assert (xx,yy)==(x,y) and (x+y)%2==0;vias+=1
        else:
            assert abs(xx-x)+abs(yy-y)==1;edges+=1
        vertices+=1;x,y,l=xx,yy,ll;done=l==0 and (x,y)==target
    for j,(xx,yy) in enumerate(points):
        ll=(mask>>j)&1
        if ll!=l:check(x,y,ll)
        while not done and (x,y)!=(xx,yy):check(x+(xx>x)-(xx<x),y+(yy>y)-(yy<y),l)
        if done:break
    if not done:check(x,y,0)
    assert done;count+=1
report=dict(passed=True,scope='Independent unit-step validation of every8115 analytic witness against all actual M11 landing reservations, grid bounds, orthogonal edges and even-parity vias. Ignores dynamic congestion and generator cap; no global feasibility or physical acceptance claim.',cases=count,vertices=vertices,wire_edges=edges,vias=vias,elapsed_seconds=time.time()-started,input_sha256=hashlib.sha256((root/'input.txt').read_bytes()).hexdigest(),analytic_receipt_sha256=hashlib.sha256((root/'receipt.json').read_bytes()).hexdigest(),validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(root/'witness-verification798.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps(report))
