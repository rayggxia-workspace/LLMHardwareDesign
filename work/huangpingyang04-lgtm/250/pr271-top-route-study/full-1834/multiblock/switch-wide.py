"""Continue the PR #271 A escape overlay, preserving the previous 320 paths."""
import argparse
from collections import defaultdict, Counter
import hashlib
import json
from pathlib import Path

NATIVE_SHA = "26143726bfff2ed0b5ed10382eab77e7286a483e7d9686a2b8a39557f661c248"
TECH_SHA = "930e87e6f1ab12e49edbb8e2fd474f2dfa3b1dfb4598c63f55440362d3ad8edc"
ORIGINAL_SHA = "31ffb0b6e7ec5fc05b39bc93b340f892cb2b99097a01a24f8f4f3e24ba9115e8"
PLACEMENT_SHA = "6cdb63981f539c8f02b35bbba592931be2eec9e3b0b67299828253b05415a744"
LOCKED = {
    "lower-evidence.json": "9563f3696e9233c8e5cc732546a0668945adb166e762b3ee133f9a1396b11460",
    "lower-paths.txt": "36a99a07b9fe9fb1b31a6951d1ca4ccc9eaab8d7c8437066b7d32f0dcb3333c7",
    "lower-plan.json": "d7b90deec995ff2e075ddc4120db34d7993360983e6dfa490dc1b86c58442af6",
    "derived-spec.json": "a054431a46dd05f5989a44bdaa19ffae878a539240cd3f39c0130b8ec5af429c",
}
LAYERS = dict(zip(("metal7", "metal8", "metal9", "metal10", "via7", "via8", "via9"), range(7)))
METAL_HALF = (400, 400, 800, 800)
CUT_HALF = (400, 400, 800)
CUT_SPACE = (880, 880, 1760)
STEP = 1600


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(path, obj):
    with path.open("x") as f:
        json.dump(obj, f, sort_keys=True, separators=(",", ":"))
        f.write("\n")


def rect(a, b, half):
    return (min(a[0], b[0])-half, min(a[1], b[1])-half, max(a[0], b[0])+half, max(a[1], b[1])+half)


def contains(a, b):
    return a[0] <= b[0] <= b[2] <= a[2] and a[1] <= b[1] <= b[3] <= a[3]


def too_close(a, b, gap):
    return max(a[0]-b[2], b[0]-a[2]) < gap and max(a[1]-b[3], b[1]-a[3]) < gap


def space(layer, a, b):
    width = max(min(a[2]-a[0], a[3]-a[1]), min(b[2]-b[0], b[3]-b[1]))
    if layer >= 4:
        return CUT_SPACE[layer-4]
    if layer >= 2:
        return 3000 if width >= 3000 else 1600
    for limit, gap in [(3000, 3000), (1800, 1800), (1000, 1000)]:
        if width >= limit:
            return gap
    return 800


class Checker:
    def __init__(self, shapes):
        self.shapes = defaultdict(list)
        for owner, layer, box in shapes:
            self.add(owner, layer, box)

    def bins(self, box, margin=0):
        for i in range((box[0]-margin)//19800, (box[2]+margin)//19800+1):
            for j in range((box[1]-margin)//19800, (box[3]+margin)//19800+1):
                yield i, j

    def add(self, owner, layer, box):
        for key in self.bins(box):
            self.shapes[layer, key].append((owner, box))

    def verify(self, owner, layer, box):
        for key in self.bins(box, 3000):
            for other, foreign in self.shapes[layer, key]:
                if other == owner and (layer < 4 or box == foreign):
                    continue
                assert not too_close(box, foreign, space(layer, box, foreign)), (owner, layer, box, other, foreign)


def path_records(path):
    with path.open() as stream:
        for line in stream:
            index, target, length = map(int, line.split())
            points = [tuple(map(int, next(stream).split())) for _ in range(length)]
            assert length > 1
            yield index, target, points


def shapes_for(owner, path, pad, area, step):
    result = []
    cuts = defaultdict(list)
    for a, b in zip(path, path[1:]):
        layer = a[2]
        assert 0 <= layer < 4 and 0 <= b[2] < 4
        if layer == b[2]:
            assert ((abs(a[0]-b[0]) == step and a[1] == b[1]) if layer % 2 == 0
                    else (a[0] == b[0] and abs(a[1]-b[1]) == step))
            result.append((owner, layer, rect(a, b, METAL_HALF[layer])))
        else:
            assert a[:2] == b[:2] and abs(layer-b[2]) == 1
            v = min(layer,b[2])
            cut = rect(a,a,CUT_HALF[v])
            assert all(not too_close(cut, other, CUT_SPACE[v]) for other in cuts[v])
            cuts[v].append(cut)
            result.extend([(owner,layer,rect(a,a,METAL_HALF[layer])),
                          (owner,b[2],rect(a,a,METAL_HALF[b[2]])),
                          (owner,4+v,cut)])
    result.append((owner,3,pad))
    assert all(contains(area, item[2]) for item in result)
    return result


def source(args):
    original = args.handoff/"top-1834/algorithm2-input.json"
    placement_path = args.handoff/"placement.json"
    assert sha(original) == ORIGINAL_SHA and sha(placement_path) == PLACEMENT_SHA
    assert sha(args.native) == NATIVE_SHA and sha(args.tech) == TECH_SHA
    for name, checksum in LOCKED.items():
        assert sha(args.locked/name) == checksum, name
    spec=read(original)
    fixed=read(args.locked/"derived-spec.json")
    previous=read(args.locked/"lower-evidence.json")
    placement=read(placement_path)
    assert len(spec["nets"]) == 1834 and previous["route_count"] == 320
    assert fixed["nets"] == spec["nets"] and fixed["technology"] == spec["technology"]
    dx,dy=placement["placement_dbu"]["sw"]
    shapes = []
    ports = defaultdict(set)
    with args.native.open() as src:
        assert "dbu_per_um=2000" in next(src)
        for line in src:
            if line.startswith("#"):
                continue
            owner,layer,kind,l,b,r,t=line.rstrip("\n").split("\t")
            box=(int(l)+dx,int(b)+dy,int(r)+dx,int(t)+dy)
            who=int(owner[1:]) if not kind.endswith("obs") and owner.startswith("n") and owner[1:].isdigit() else -1
            shapes.append((who,LAYERS[layer],box))
            if layer=="metal10" and kind=="block-port":
                ports[box].add(who)

    old_plan=read(args.locked/"lower-plan.json")
    old_jobs={i:(owner,terminal,pin) for i,owner,terminal,pin in old_plan["jobs"]}
    old_rebound={row["net"]:row for row in previous["rebound"]}
    frozen=[]
    for i,t,path in path_records(args.locked/"lower-paths.txt"):
        net=spec["nets"][i]["id"]
        owner,terminal,pin=old_jobs[i]
        assert ports[tuple(terminal)] == {owner}
        a=old_plan["targets"][t]
        pad=rect(a[:2],a[:2],2000)
        assert list(pad)==old_rebound[net]["new_m10"] and old_rebound[net]["pin"]==pin
        assert fixed["pins"][pin]==[list(pad)]
        assert t >= 0 and net in old_rebound and contains(terminal,rect(path[0],path[0],800))
        assert contains(pad,rect(path[-1],path[-1],800))
        frozen.extend(shapes_for(owner,[(x,y,layer+2) for x,y,layer in path],pad,old_plan["area"],3200))
    assert len(frozen)>320
    return spec,fixed,previous,placement,shapes,ports,frozen,old_jobs


def snap_up(a,phase,step):
    return a+(phase-a)%step


def snap_nearest(a,phase,step):
    return a+step//2-(a+step//2-phase)%step


def prepare(args,data):
    spec,fixed,previous,placement,shapes,ports,frozen,old_jobs=data
    boxes=placement["boxes_dbu"]
    l,b,r,t=boxes["sw"]
    dx,dy=placement["placement_dbu"]["sw"]
    area=(4350000,6935000,8850000,8445000)
    assert all(not too_close(area,rect,0) for which,rect in boxes.items() if which!="sw")
    assert contains(spec["technology"]["bounds"],area)
    x0,y0=snap_up(area[0]+2500,dx+190,3200),snap_up(area[1]+2500,dy+140,3200)
    nx=(area[2]-2500-x0)//STEP+1
    ny=(area[3]-2500-y0)//STEP+1
    tx,ty=spec["technology"]["origin"]
    p=spec["technology"]["pitch"]

    pins=defaultdict(list)
    for shapes_list in fixed["pins"].values():
        for rectangle in shapes_list:
            left,bot,right,top=rectangle
            for i in range(left//p,right//p+1):
                for j in range(bot//p,top//p+1):
                    pins[i,j].append(tuple(rectangle))
    goals=[]
    for x in range(snap_up(area[0]+5000,tx,args.site_pitch*p),area[2]-5000,args.site_pitch*p):
        for y in range(snap_up(area[1]+5000,ty,args.site_pitch*p),area[3]-5000,args.site_pitch*p):
            pad=rect((x,y),(x,y),2000)
            far_lane = (
                x < 5300000 or x > 7520000 or
                (6980000 < y < 7240000) or (8380000 < y < 8420000)
            )
            if not far_lane or too_close(pad,(l,b,r,t),19000):
                continue
            ex,ey=snap_nearest(x,dx+190,3200),snap_nearest(y,dy+140,STEP)
            if abs(x-ex)>1200 or abs(y-ey)>1200:
                continue
            if any(too_close(pad,pin,4400) for ix in range(x//p-2,x//p+3)
                   for iy in range(y//p-2,y//p+3) for pin in pins[ix,iy]):
                continue
            goals.append((x,y,ex,ey))
    assert len(goals)>590
    old={record["net"] for record in previous["rebound"]}
    jobs=[]
    for i,(owner,terminal,pin) in old_jobs.items():
        if spec["nets"][i]["id"] in old:
            continue
        assert ports[tuple(terminal)]=={owner}
        x,y=(terminal[0]+terminal[2])//2,(terminal[1]+terminal[3])//2
        depth=min(x-l,r-x,y-b,t-y)
        rank=depth if args.order=="edge" else -depth
        jobs.append((rank,i,owner,terminal,pin))
    jobs.sort()
    assert len(jobs)==589
    with (args.run/"input.txt").open("x") as out:
        print(x0,y0,nx,ny,len(shapes)+len(frozen),file=out)
        for owner,layer,rc in [*shapes,*frozen]:
            print(owner,layer,*rc,file=out)
        print(len(goals),file=out)
        for goal in goals:
            x,y,_,_=goal
            side=max(range(4),key=(l-x,x-r,b-y,y-t).__getitem__)
            print(*goal,side,file=out)
        print(len(jobs),file=out)
        for _,i,owner,terminal,_ in jobs:
            print(i,owner,*terminal,file=out)
    write(args.run/"plan.json",{
        "area":area,"mesh":[x0,y0,nx,ny],"switch_box":boxes["sw"],"sites":goals,
        "jobs":[(i,owner,terminal,pin) for _,i,owner,terminal,pin in jobs],
        "native_shape_count":len(shapes),"locked_shape_count":len(frozen)
    })
    print("candidates",len(jobs),"landing_sites",len(goals),"native_shapes",len(shapes),
          "locked_shapes",len(frozen),flush=True)


def verify(args,data):
    spec,fixed,previous,placement,shapes,ports,frozen,_=data
    plan=read(args.run/"plan.json")
    candidates={i:(owner,terminal,pin) for i,owner,terminal,pin in plan["jobs"]}
    x0,y0,nx,ny=plan["mesh"]
    occupied=Checker([*shapes,*frozen])
    moved=set()
    used=set()
    rebound=[]
    vias=Counter()
    use=Counter()
    for index,target,path in path_records(args.run/"paths.txt"):
        assert index in candidates and index not in moved and target not in used
        moved.add(index)
        used.add(target)
        owner,terminal,pin=candidates[index]
        assert ports[tuple(terminal)]=={owner}
        assert fixed["pins"][pin]==spec["pins"][pin]==[terminal]
        x,y,ex,ey=plan["sites"][target]
        pad=rect((x,y),(x,y),2000)
        assert path[0][2]==3 and path[-1]==(ex,ey,3)
        assert contains(terminal,rect(path[0],path[0],800))
        assert contains(pad,rect(path[-1],path[-1],800)) and not too_close(pad,plan["switch_box"],0)
        for a,b,layer in path:
            assert 0<=layer<=3 and x0<=a<x0+nx*STEP and y0<=b<y0+ny*STEP
            assert (a-x0)%STEP==(b-y0)%STEP==0
            assert layer<2 or ((b-y0 if layer==2 else a-x0)%(2*STEP)==0)
        additions=shapes_for(owner,path,pad,plan["area"],STEP)
        for who,layer,rc in additions:
            occupied.verify(who,layer,rc)
        for who,layer,rc in additions:
            occupied.add(who,layer,rc)
        used_layers=sorted({p[2]+7 for p in path})
        use.update(used_layers)
        ncuts=Counter(min(a[2],b[2])+7 for a,b in zip(path,path[1:]) if a[2]!=b[2])
        vias.update(ncuts)
        fixed["pins"]["frozen_escape_source/"+pin]=[terminal]
        fixed["pins"][pin]=[list(pad)]
        rebound.append({"net":spec["nets"][index]["id"],"pin":pin,"native_owner":owner,
                        "old_m10":terminal,"new_m10":pad,"metal_layers":used_layers,
                        "via_counts":dict(ncuts)})
    ids=[x["net"] for x in previous["rebound"]+rebound]
    assert len(ids)==len(set(ids))==320+len(moved) and len(spec["nets"])==1834
    result={
        "type":"continued-m7-m10-geometric-overlay",
        "original_handoff_sha256":ORIGINAL_SHA,"placement_sha256":PLACEMENT_SHA,
        "native_tsv_sha256":NATIVE_SHA,"tech_sha256":TECH_SHA,
        "locked_escape_sha256":LOCKED["lower-evidence.json"],"locked_count":320,
        "new_lower_routes_sha256":sha(args.run/"paths.txt"),"additional_count":len(moved),
        "route_count":len(ids),"top_only_sw_crossings":909-len(ids),
        "additional_layer_nets":dict(use),"additional_via_counts":dict(vias),
        "rebound":previous["rebound"]+rebound
    }
    write(args.run/"lower-evidence.json",result)
    fixed["context"]["lower_escape_overlay_sha256"]=sha(args.run/"lower-evidence.json")
    write(args.run/"derived-spec.json",fixed)
    print({k:v for k,v in result.items() if k!="rebound"},flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("prepare","verify"))
    for name in ("handoff","native","tech","locked","run"):
        p.add_argument(name,type=Path)
    p.add_argument("--order",choices=("edge","deep"),default="edge")
    p.add_argument("--site-pitch",type=int,choices=(1,2,3),default=3)
    args=p.parse_args()
    (prepare if args.mode=="prepare" else verify)(args,source(args))
