"""Deterministic obstacle-event routing of bounded single-via C8 escapes.

All actual foreign upper rectangles remain obstacles, including unreported
nets, fixed via8 enclosures and pins. This is a finite preflight algorithm;
actual database/DRC/RC/STA/function gates remain independently mandatory.
"""
import collections
import math
from native_escape import parse,path_length
from native_c8_escape import propose
from native_c8_geometry import UPPER,render,replace,Obstacles


def pin_center(proof,name):
    ports=proof['ports'][name];assert len(ports)==1 and ports[0]['layer']=='metal10'
    box=ports[0]['bbox_dbu'];assert all(v%2==0 for v in [box[0]+box[2],box[1]+box[3]])
    return ((box[0]+box[2])//2,(box[1]+box[3])//2)


def events(index,name,pin,old,die):
    # Fixed algorithm scope: original pin/via9 span plus 6.4um on each side.
    # This restricts candidate locations only; no obstacle is clipped.
    radius=12800;grid=10
    roi=(max(die[0]+800,min(pin[0],old[0])-radius),max(die[1]+800,min(pin[1],old[1])-radius),
         min(die[2]-800,max(pin[0],old[0])+radius),min(die[3]-800,max(pin[1],old[1])+radius))
    assert roi[0]<=roi[2]and roi[1]<=roi[3]
    def down(v):return v//grid*grid
    def up(v):return -((-v)//grid)*grid
    xs={pin[0],old[0],up(roi[0]),down(roi[2])};ys={pin[1],old[1],up(roi[1]),down(roi[3])};obstacles=set()
    for layer in UPPER:
        spacing=1760 if layer=='via9'else 1600
        for other,_,kind,box in index.query(layer,roi,spacing+800):
            if other==name:continue
            obstacles.add((spacing,box))
            xs.update([down(box[0]-800-spacing),up(box[2]+800+spacing)])
            ys.update([down(box[1]-800-spacing),up(box[3]+800+spacing)])
    xs={x for x in xs if roi[0]<=x<=roi[2]};ys={y for y in ys if roi[1]<=y<=roi[3]}
    targets={(x,y)for x in xs for y in ys}
    def root_ceil(square):
        root=math.isqrt(square);return root+(root*root<square)
    # Exact outward manufacturing-grid events at rounded obstacle corners.
    for y in sorted(ys):
        for spacing,b in obstacles:
            dy=max(0,y-800-b[3],b[1]-y-800)
            if dy<spacing:
                dx=root_ceil(spacing*spacing-dy*dy)
                targets.update([(down(b[0]-800-dx),y),(up(b[2]+800+dx),y)])
    for x in sorted(xs):
        for spacing,b in obstacles:
            dx=max(0,x-800-b[2],b[0]-x-800)
            if dx<spacing:
                dy=root_ceil(spacing*spacing-dx*dx)
                targets.update([(x,down(b[1]-800-dy)),(x,up(b[3]+800+dy))])
    targets={p for p in targets if roi[0]<=p[0]<=roi[2]and roi[1]<=p[1]<=roi[3]and all(v%grid==0 for v in p)}
    return targets,dict(roi_dbu=roi,manufacturing_grid_dbu=grid,event_obstacles=len(obstacles),event_targets=len(targets),radius_dbu=radius)


def legalize(proof,by_net,die):
    original=proof['source_routes'];assert set(original)==set(proof['reported_nets'])
    scene={n:list(rows)for n,rows in by_net.items()};texts={};plans={};binding={}
    for name,text in original.items():
        pin=pin_center(proof,name);new,plan=propose(text,pin)
        scene[name]=replace(scene[name],text,new);texts[name]=new;plans[name]=plan
        binding[name]=len(render(parse(text)[1]))
    index=Obstacles(scene)
    residual=[v for name in original for v in index.violations(name,scene[name])]
    moving=sorted({v['net']for v in residual})
    # Rip up only the selected upper paths, preserving every other actual
    # shape, including duplicate lower-via metal and fixed BPin rectangles.
    for name in moving:
        before=collections.Counter(by_net[name]);removed=collections.Counter(render(parse(original[name])[1]))
        assert not removed-before
        remaining=list((before-removed).elements());scene[name]=remaining
        index.remove(name);index.add(name,remaining)
    routes={};failures={}
    for name in moving:
        pin=pin_center(proof,name);paths=parse(original[name])[1]
        old=next(p['points'][0][:2]for p in paths if p['layer']=='metal9'and p['via'])
        lower={p['points'][0][:2]for p in paths if p['layer']=='metal8'and p['via']};assert len(lower)==1
        lower=next(iter(lower));limit=sum(path_length(paths,m)for m in ['metal9','metal10'])
        targets,record=events(index,name,pin,old,die)
        def length(p):return sum(abs(a-b)for a,b in zip(pin,p))+sum(abs(a-b)for a,b in zip(lower,p))
        targets=sorted((p for p in targets if length(p)<=limit),key=lambda p:(length(p),sum(abs(a-b)for a,b in zip(pin,p)),p))
        record.update(length_budget_dbu=limit,length_feasible_targets=len(targets));attempts=0;accepted=None
        for target in targets:
            for nine,ten in [(True,True),(False,True),(True,False),(False,False)]:
                attempts+=1
                try:new,plan=propose(original[name],pin,target,nine,ten)
                except AssertionError:continue
                shapes=render(plan['final_paths'])
                if any(not(die[0]<=b[0]<b[2]<=die[2]and die[1]<=b[1]<b[3]<=die[3])for l,k,b in shapes):continue
                # Include retained via8/ports in this gate, so a fixed lower
                # conflict cannot be hidden by rerouting only the new paths.
                if index.violations(name,scene[name]+shapes):continue
                accepted=(new,plan,shapes,target,nine,ten);break
            if accepted:break
        record['attempted_routes']=attempts
        if accepted is None:
            failures[name]=record
            # Keep a complete diagnostic scene even when this bounded router
            # cannot find a legal escape. No partial source is qualified.
            restored=replace(by_net[name],original[name],texts[name]);index.remove(name);index.add(name,restored);scene[name]=restored
        else:
            new,plan,shapes,target,nine,ten=accepted
            scene[name]+=shapes;index.add(name,shapes);texts[name]=new;plans[name]=plan
            record.update(landing_dbu=target,m9_horizontal_first=nine,m10_horizontal_first=ten,final_upper_length_dbu=length(target))
        routes[name]=record
    remaining=[v for name in original for v in index.violations(name,scene[name])]
    changes={n:plans[n]for n in plans if plans[n]['changed']}
    return dict(passed=not failures and not remaining,reported_nets=len(original),faithful_native_rendered_shapes=binding,
                initial_fixed_via_violations=residual,moving_nets=moving,routing=routes,failures=failures,remaining=remaining,
                changed_nets=sorted(changes),qualified_hard_macro=False,
                scope='SHA-bound source rectangles and finite obstacle-event preflight only; actual ODB editing, full native rules, regenerated RC/STA/function and all macro gates remain mandatory'),texts,plans,scene
