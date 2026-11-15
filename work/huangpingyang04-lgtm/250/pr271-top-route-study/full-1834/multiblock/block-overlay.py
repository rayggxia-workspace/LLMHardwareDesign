"""Place and verify disjoint lower escape overlays around the fixed #271 blocks."""
import argparse
from collections import Counter, defaultdict
import gzip
from pathlib import Path

import lower_rules as geom


ASSEMBLIES = {
    "U0": ("U.Gather", (4315000, 4535000, 6970000, 6900000), 280, 85),
    "C0": ("C", (0, 4535000, 4300000, 7390000), 145, 65),
    "dma": ("DMA", (9545000, 0, 13595000, 4200000), 230, 100),
    "P0": ("P", (0, 0, 3020000, 4500000), 100, 50),
    "P1": ("P", (3150000, 0, 6330000, 4500000), 105, 50),
    "P2": ("P", (6450000, 0, 9530000, 4510000), 110, 50),
    "mc": ("MC", (5230000, 8465000, 7730000, 10300000), 105, 55),
}
SW_FIXED_AREA=(5450000,6930000,7332000,8445000)
BASE_HASH="2542c710671fb334c6c03962d4a3a460a13b89cbe4d915b11b82bce07e3cd093"
SW_HASH="d3692dcaf6e33253c985d579fc9b382164c7fd8b0f22e36214a1e9d23ab189ba"
PRIOR_TOP_HASH="de10b19a828840f3105fd6a9fa3f192a2094b0549f6714dc0601c598c8fec5b8"


def load(args):
    assert geom.sha(args.placement)==geom.PLACEMENT_SHA
    assert geom.sha(args.spec)==BASE_HASH
    assert geom.sha(args.prior)==PRIOR_TOP_HASH
    prior=geom.read(args.prior)
    assert prior["geometry_check"]["passed"] and len(prior["routes"])==734
    spec=geom.read(args.spec)
    floor=geom.read(args.placement)
    assert floor["variant"]=="pr271_A" and len(spec["nets"])==1834
    boxes=floor["boxes_dbu"]
    limits=spec["technology"]["bounds"]
    for block,(_,area,_,_) in ASSEMBLIES.items():
        assert geom.contains(limits,area) and geom.contains(area,boxes[block])
        assert not geom.too_close(area,SW_FIXED_AREA,3200)
        for other,extent in boxes.items():
            if other!=block:
                assert not geom.too_close(area,extent,3200),(block,other)
        for other,(_,extent,_,_) in ASSEMBLIES.items():
            if other!=block:
                assert not geom.too_close(area,extent,3200),(block,other,area,extent)
    return spec,floor,prior


def frozen(archive, dx,dy):
    shapes=[]
    pins=defaultdict(set)
    with gzip.open(archive,"rt") as stream:
        assert "dbu_per_um=2000" in next(stream)
        for line in stream:
            if line.startswith("#"):
                continue
            tag,layer,kind,l,b,r,t=line.rstrip("\n").split("\t")
            owner=int(tag[1:]) if not kind.endswith("obs") and tag.startswith("n") and tag[1:].isdigit() else -1
            box=(int(l)+dx,int(b)+dy,int(r)+dx,int(t)+dy)
            shapes.append((owner,geom.LAYERS[layer],box))
            if kind=="block-port" and layer=="metal10":
                pins[box].add(owner)
    return shapes,pins


def crosses(point,box):
    return not geom.contains(box,point)


def sector(x,y,box):
    l,b,r,t=box
    return max(range(4),key=(l-x,x-r,b-y,y-t).__getitem__)


def prepare(args,spec,floor,prior,shapes,ports):
    block=args.block
    _,area,goal,per_side=ASSEMBLIES[block]
    l,b,r,t=floor["boxes_dbu"][block]
    box=(l,b,r,t)
    dx,dy=floor["placement_dbu"][block]
    x0=geom.snap_up(area[0]+2500,dx+190,3200)
    y0=geom.snap_up(area[1]+2500,dy+140,3200)
    nx=(area[2]-2500-x0)//geom.STEP+1
    ny=(area[3]-2500-y0)//geom.STEP+1
    ox,oy=spec["technology"]["origin"]
    pitch=spec["technology"]["pitch"]
    cells=defaultdict(list)
    active={p for net in spec["nets"] for p in (net["driver"],*net["sinks"])}
    for pin,rectangles in spec["pins"].items():
        if pin not in active:
            continue
        for a in rectangles:
            for ix in range(a[0]//pitch,a[2]//pitch+1):
                for iy in range(a[1]//pitch,a[3]//pitch+1):
                    cells[ix,iy].append(a)
    sites=[]
    target_spacing=2*pitch
    for x in range(geom.snap_up(area[0]+6000,ox,target_spacing),area[2]-6000,target_spacing):
        for y in range(geom.snap_up(area[1]+6000,oy,target_spacing),area[3]-6000,target_spacing):
            pad=geom.rect((x,y),(x,y),2000)
            if geom.too_close(pad,box,16000):
                continue
            ex=geom.snap_nearest(x,dx+190,3200)
            ey=geom.snap_nearest(y,dy+140,geom.STEP)
            if abs(x-ex)>1200 or abs(y-ey)>1200:
                continue
            if any(geom.too_close(pad,p,4400) for i in range(x//pitch-2,x//pitch+3)
                   for j in range(y//pitch-2,y//pitch+3) for p in cells.get((i,j),())):
                continue
            sites.append((x,y,ex,ey,sector(x,y,box)))

    jobs=[]
    skipped=Counter()
    for index,net in enumerate(spec["nets"]):
        terms=[net["driver"],*net["sinks"]]
        local=[pin for pin in terms if pin.startswith(block+"/")]
        if not local:
            continue
        if len(local)!=1:
            skipped["multiple_ports_in_block"]+=1
            continue
        pin=local[0]
        rectangles=spec["pins"][pin]
        if len(rectangles)!=1:
            skipped["port_has_multiple_shapes"]+=1
            continue
        terminal=rectangles[0]
        if not geom.contains(box,terminal) or not all(
            not geom.too_close(other,box,0) for p in terms if p!=pin for other in spec["pins"][p]
        ):
            skipped["not_an_isolated_crossing"]+=1
            continue
        owners=ports.get(tuple(terminal),set())
        if len(owners)!=1 or next(iter(owners))<=0:
            skipped["no_exact_owned_native_port"]+=1
            continue
        owner,=owners
        x=(terminal[0]+terminal[2])//2
        y=(terminal[1]+terminal[3])//2
        depth=min(x-l,r-x,y-b,t-y)
        density=sum(len(cells.get((i,j),())) for i in range(x//pitch-2,x//pitch+3)
                    for j in range(y//pitch-2,y//pitch+3))
        jobs.append((net["id"] in prior["routes"],-density,depth,index,owner,terminal,pin))
    jobs.sort()
    if len(jobs)<30 or not sites:
        raise RuntimeError((block,len(jobs),len(sites),dict(skipped)))
    with (args.run/"input.txt").open("x") as out:
        print(x0,y0,nx,ny,len(shapes),file=out)
        for o,get,area_box in shapes:
            print(o,get,*area_box,file=out)
        print(len(sites),file=out)
        for s in sites:
            print(*s,file=out)
        print(len(jobs),file=out)
        for _,_,_,i,o,term,_ in jobs:
            print(i,o,*term,file=out)
    geom.write(args.run/"plan.json",{
        "block":block,"area":area,"mesh":[x0,y0,nx,ny],"box":box,"sites":sites,
        "jobs":[(i,o,term,pin) for _,_,_,i,o,term,pin in jobs],
        "skipped":dict(skipped),"goal":goal,"side_cap":per_side,
        "archive_sha256":geom.sha(args.archive)
    })
    print("block",block,"candidates",len(jobs),"sites",len(sites),"shapes",len(shapes),"skipped",dict(skipped),flush=True)


def verify(args,spec,floor,shapes,ports):
    plan=geom.read(args.run/"plan.json")
    assert plan["block"]==args.block and geom.sha(args.archive)==plan["archive_sha256"]
    x0,y0,nx,ny=plan["mesh"]
    jobs={i:(o,t,p) for i,o,t,p in plan["jobs"]}
    marked=geom.Checker(shapes)
    moved=[]
    counts=Counter()
    layer_counts=Counter()
    chosen=set()
    net_used=set()
    for i,id,path in geom.path_records(args.run/"paths.txt"):
        assert i in jobs and i not in net_used and id not in chosen
        chosen.add(id)
        net_used.add(i)
        owner,terminal,pin=jobs[i]
        x,y,ex,ey,side=plan["sites"][id]
        pad=geom.rect((x,y),(x,y),2000)
        assert not geom.too_close(pad,plan["box"],0)
        assert ports[tuple(terminal)]=={owner}
        assert path[0][2]==3 and path[-1]==(ex,ey,3)
        assert geom.contains(terminal,geom.rect(path[0],path[0],800))
        assert geom.contains(pad,geom.rect(path[-1],path[-1],800))
        for u,v,layer in path:
            assert 0<=layer<4 and x0<=u<x0+nx*geom.STEP and y0<=v<y0+ny*geom.STEP
            assert (u-x0)%geom.STEP==(v-y0)%geom.STEP==0
            assert layer<2 or ((v-y0 if layer==2 else u-x0)%(2*geom.STEP)==0)
        additions=geom.shapes_for(owner,path,pad,plan["area"],geom.STEP)
        for who,layer,rc in additions:
            marked.verify(who,layer,rc)
        for who,layer,rc in additions:
            marked.add(who,layer,rc)
        counts[("west","east","south","north")[side]]+=1
        layer_counts.update({str(p[2]+7) for p in path})
        moved.append({"net":spec["nets"][i]["id"],"pin":pin,"native_owner":owner,
                      "old_m10":terminal,"new_m10":list(pad),"block":args.block,
                      "landing_side":("west","east","south","north")[side]})
    result={"block":args.block,"base_handoff_sha256":BASE_HASH,"archive_sha256":plan["archive_sha256"],
            "routes_sha256":geom.sha(args.run/"paths.txt"),"area":plan["area"],"count":len(moved),
            "by_side":dict(counts),"layer_counts":dict(layer_counts),"skipped":plan["skipped"],
            "rebound":moved}
    geom.write(args.run/"block-evidence.json",result)
    print({k:v for k,v in result.items() if k!="rebound"},flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("prepare","verify"))
    parser.add_argument("block",choices=tuple(ASSEMBLIES))
    for field in ("spec","placement","prior","archive","run"):
        parser.add_argument(field,type=Path)
    args=parser.parse_args()
    spec,floor,prior=load(args)
    cx,cy=floor["placement_dbu"][args.block]
    shapes,ports=frozen(args.archive,cx,cy)
    if args.mode=="prepare":
        prepare(args,spec,floor,prior,shapes,ports)
    else:
        verify(args,spec,floor,shapes,ports)
