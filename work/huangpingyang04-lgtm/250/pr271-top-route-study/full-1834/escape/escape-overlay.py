"""Build and independently check an M9/M10/V9 escape overlay for PR #271 A."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path


ORIGINAL = "31ffb0b6e7ec5fc05b39bc93b340f892cb2b99097a01a24f8f4f3e24ba9115e8"
NATIVE = "cfa2c367f37f1e6daa22741c1664fe32e16638159828321c7cfa0458617b03d4"
PLACEMENT = "6cdb63981f539c8f02b35bbba592931be2eec9e3b0b67299828253b05415a744"
PITCH = 3200
NAMES = {"metal9": 0, "metal10": 1, "via9": 2}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x") as out:
        json.dump(value, out, sort_keys=True, separators=(",", ":"))
        out.write("\n")


def contains(where, rect):
    l, b, r, t = where
    a, c, d, e = rect
    return l <= a <= d <= r and b <= c <= e <= t


def intersects(left, right):
    return min(left[2], right[2]) > max(left[0], right[0]) and min(left[3], right[3]) > max(left[1], right[1])


def shape(a, b, half=800):
    return [min(a[0], b[0])-half, min(a[1], b[1])-half, max(a[0], b[0])+half, max(a[1], b[1])+half]


def native_geometry(path, translation):
    assert digest(path) == NATIVE
    ports = defaultdict(set)
    shapes = []
    dx, dy = translation
    with path.open() as f:
        assert "dbu_per_um=2000" in next(f)
        for line in f:
            if line.startswith("#"):
                continue
            net, layer, kind, l, b, r, t = line.rstrip("\n").split("\t")
            if layer not in NAMES:
                continue
            rect = (int(l)+dx, int(b)+dy, int(r)+dx, int(t)+dy)
            owner = int(net[1:]) if net.startswith("n") and net[1:].isdigit() else -1
            shapes.append((owner, NAMES[layer], rect))
            if kind == "block-port" and layer == "metal10":
                ports[rect].add(owner)
    return shapes, ports


def snap_down(x, phase, pitch):
    return x-(x-phase)%pitch


def snap_up(x, phase, pitch):
    return x+((phase-x)%pitch)


def nearest(x, phase):
    return snap_down(x+PITCH//2, phase, PITCH)


def load(args):
    original = args.handoff / "top-1834/algorithm2-input.json"
    placement = args.handoff / "placement.json"
    assert digest(original) == ORIGINAL and digest(placement) == PLACEMENT
    spec = json.loads(original.read_bytes())
    floor = json.loads(placement.read_bytes())
    assert floor["variant"] == "pr271_A" and len(spec["nets"]) == 1834
    return spec, floor


def prepare(args, spec, floor, shapes, ports):
    dx, dy = floor["placement_dbu"]["sw"]
    l,b,r,t = floor["boxes_dbu"]["sw"]
    inner = (l-360000,b-540000,r+360000,t+140000)
    assert all(not intersects(inner, other) for inst,other in floor["boxes_dbu"].items() if inst != "sw")
    assert contains(spec["technology"]["bounds"], inner)
    x0 = snap_up(inner[0]+2000, dx+190, PITCH)
    y0 = snap_up(inner[1]+2000, dy+140, PITCH)
    nx = (inner[2]-2000-x0)//PITCH+1
    ny = (inner[3]-2000-y0)//PITCH+1

    vx, vy = spec["technology"]["origin"]
    tpitch = spec["technology"]["pitch"]
    old_pin_bins = defaultdict(list)
    for rects in spec["pins"].values():
        for rect in rects:
            xx, yy = (rect[0]+rect[2])//2, (rect[1]+rect[3])//2
            old_pin_bins[xx//tpitch, yy//tpitch].append(rect)

    landing_pitch = args.site_pitch * tpitch
    targets = []
    for x in range(snap_up(inner[0]+4000,vx,landing_pitch),inner[2]-4000,landing_pitch):
        for y in range(snap_up(inner[1]+4000,vy,landing_pitch),inner[3]-4000,landing_pitch):
            pad = shape((x,y),(x,y),2000)
            if intersects((l-20000,b-20000,r+20000,t+20000),pad):
                continue
            xn,yn = nearest(x,dx+190),nearest(y,dy+140)
            if abs(x-xn)>1200 or abs(y-yn)>1200:
                continue
            if any(too_close(pad, rect, 4400)
                   for ix in range(x//tpitch-2,x//tpitch+3)
                   for iy in range(y//tpitch-2,y//tpitch+3)
                   for rect in old_pin_bins.get((ix,iy),())):
                continue
            targets.append([x,y,xn,yn])
    cut_blob = json.loads(args.cut.read_bytes())
    assert cut_blob["input_sha256"] == ORIGINAL and cut_blob["placement_sha256"] == PLACEMENT
    cut = set(cut_blob["cuts"]["sw/declared block-outline cut"]["net_ids"])
    assert len(cut)==909
    prior = json.loads(args.prior.read_bytes())
    assert prior["geometry_check"]["passed"] and len(prior["routes"]) == 501
    jobs = []
    for index, net in enumerate(spec["nets"]):
        if net["id"] not in cut:
            continue
        all_pins = [net["driver"],*net["sinks"]]
        pin, = [name for name in all_pins if name.startswith("sw/")]
        terminal, = spec["pins"][pin]
        assert contains((l,b,r,t),terminal)
        assert all(not intersects((l,b,r,t), p) for name in all_pins if name != pin for p in spec["pins"][name])
        owner, = ports[tuple(terminal)]
        assert owner > 0
        x,y=(terminal[0]+terminal[2])//2,(terminal[1]+terminal[3])//2
        cost=min(x-l,r-x,y-b,t-y)
        jobs.append((net["id"] in prior["routes"] if args.prefer_missing else False,cost,index,owner,terminal,pin))
    assert len(jobs)==909
    jobs.sort()
    with (args.out/"lower-input.txt").open("x") as out:
        print(x0,y0,nx,ny,len(shapes),file=out)
        for owner,layer,rect in shapes:
            print(owner,layer,*rect,file=out)
        print(len(targets),file=out)
        for target in targets:
            print(*target,file=out)
        print(len(jobs),file=out)
        for _,_,i,owner,term,_ in jobs:
            print(i,owner,*term,file=out)
    write(args.out/"lower-plan.json", {
        "source_placement_sha256":PLACEMENT,"source_handoff_sha256":ORIGINAL,
        "native_geometry_sha256":NATIVE,"area":inner,"switch_box":[l,b,r,t],
        "mesh":[x0,y0,nx,ny],"site_pitch_multiple":args.site_pitch,
        "targets":targets,"jobs":[[i,owner,term,pin] for _,_,i,owner,term,pin in jobs]})
    print("escape candidates",len(jobs),"landing sites",len(targets),"native rectangles",len(shapes),flush=True)


def too_close(a, b, gap):
    return max(a[0]-b[2],b[0]-a[2])<gap and max(a[1]-b[3],b[1]-a[3])<gap


class Rectangles:
    """Verify spacing from the reconstructed rectangle geometry."""
    def __init__(self, shapes):
        self.cells=defaultdict(list)
        for owner,layer,rect in shapes:
            self.add(owner,layer,rect)

    @staticmethod
    def bins(box,margin=0):
        l,b,r,t=box
        for i in range((l-margin)//19800,(r+margin)//19800+1):
            for j in range((b-margin)//19800,(t+margin)//19800+1):
                yield i,j

    def add(self,owner,layer,rect):
        for key in self.bins(rect):
            self.cells[layer,key].append((owner,tuple(rect)))

    def check(self, owner, layer, rect):
        rc=tuple(rect)
        width=min(rc[2]-rc[0],rc[3]-rc[1])
        for key in self.bins(rc,3000):
            for other, check in self.cells[layer,key]:
                if other==owner and (layer!=2 or rc==check):
                    continue
                check_width=min(check[2]-check[0],check[3]-check[1])
                gap=1760 if layer==2 else (3000 if max(width,check_width)>=3000 else 1600)
                assert not too_close(rc,check,gap),(owner,layer,rc,other,check,gap)


def verify(args, spec, floor, shapes, ports):
    plan=json.loads((args.out/"lower-plan.json").read_bytes())
    jobs={i:(owner,term,pin) for i,owner,term,pin in plan["jobs"]}
    x0,y0,nx,ny=plan["mesh"]
    occupancy=Rectangles(shapes)
    moved={}
    used=set()
    results=[]
    lengths=Counter()
    source=args.out/"lower-paths.txt"
    with source.open() as records:
        for header in records:
            index,target,count=map(int,header.split())
            net=spec["nets"][index]
            assert net["id"] not in moved and target not in used and count>1
            used.add(target)
            owner,terminal,pin=jobs[index]
            assert ports[tuple(terminal)]=={owner} and spec["pins"][pin]==[terminal]
            x,y,ex,ey=plan["targets"][target]
            pad=shape((x,y),(x,y),2000)
            path=[tuple(map(int,next(records).split())) for _ in range(count)]
            assert path[0][2]==1 and path[-1]==(ex,ey,1)
            assert contains(terminal,shape(path[0],path[0]))
            assert contains(pad,shape(path[-1],path[-1])) and not intersects(plan["switch_box"],pad)
            assert contains(plan["area"],pad)
            for p in path:
                px,py,layer=p
                assert layer in (0,1) and (px-x0)%PITCH==(py-y0)%PITCH==0
                assert x0<=px<x0+nx*PITCH and y0<=py<y0+ny*PITCH
            additions=[]
            cut_coords=set()
            for a,b in zip(path,path[1:]):
                ab=shape(a,b)
                assert contains(plan["area"],ab)
                if a[2]==b[2]:
                    assert (abs(a[0]-b[0])==PITCH and a[1]==b[1]) if a[2]==0 else (a[0]==b[0] and abs(a[1]-b[1])==PITCH)
                    additions.append((a[2],ab))
                    lengths[a[2]]+=PITCH
                else:
                    assert a[:2]==b[:2]
                    assert all(abs(cx-a[0])>=3360 or abs(cy-a[1])>=3360 for cx,cy in cut_coords)
                    cut_coords.add(a[:2])
                    additions.extend((layer,ab) for layer in (0,1,2))
            for layer,rect in [*additions,(1,pad)]:
                occupancy.check(owner,layer,rect)
            for layer,rect in [*additions,(1,pad)]:
                occupancy.add(owner,layer,rect)
            # Preserve original metal as a protected native rectangle, with the named top terminal rebinding.
            spec["pins"]["frozen_escape_source/"+pin]=[terminal]
            spec["pins"][pin]=[pad]
            moved[net["id"]]=pin
            results.append({"net":net["id"],"pin":pin,"native_owner":owner,
                            "old_m10":terminal,"new_m10":pad,"v9":len(cut_coords)})
    assert len(moved)==len(results) and len(spec["nets"])==1834
    overlay={"type":"lower-m9-m10-geometric-overlay","native_tsv_sha256":NATIVE,
             "placement_sha256":PLACEMENT,"original_handoff_sha256":ORIGINAL,
             "lower_routes_sha256":digest(source),"route_count":len(moved),
             "top_only_sw_crossings":909-len(moved),"m9_m10_wire_dbu":dict(lengths),
             "rebound":results}
    write(args.out/"lower-evidence.json",overlay)
    spec["context"]["lower_escape_overlay_sha256"]=digest(args.out/"lower-evidence.json")
    write(args.out/"derived-spec.json",spec)
    print({k:v for k,v in overlay.items() if k!="rebound"},flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=["prepare","verify"])
    parser.add_argument("handoff",type=Path)
    parser.add_argument("native",type=Path)
    parser.add_argument("cut",type=Path)
    parser.add_argument("prior",type=Path)
    parser.add_argument("out",type=Path)
    parser.add_argument("--site-pitch",type=int,default=2,choices=[1,2,3])
    parser.add_argument("--prefer-missing",action="store_true")
    args=parser.parse_args()
    spec,floor=load(args)
    shapes,ports=native_geometry(args.native,floor["placement_dbu"]["sw"])
    if args.mode=="prepare":
        prepare(args,spec,floor,shapes,ports)
    else:
        verify(args,spec,floor,shapes,ports)
