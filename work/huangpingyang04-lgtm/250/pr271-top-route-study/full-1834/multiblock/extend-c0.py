"""Extend C0 at the local capacity cut while preserving its first 145 escapes."""
import argparse
from pathlib import Path
import lower_rules as g


AREA=(2240000,6800000,2400000,7120000)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("prepare","merge"))
    p.add_argument("locked",type=Path)
    p.add_argument("run",type=Path)
    a=p.parse_args()
    plan=g.read(a.locked/"plan.json")
    evidence=g.read(a.locked/"block-evidence.json")
    assert plan["block"]==evidence["block"]=="C0" and evidence["count"]==145
    assert g.sha(a.locked/"paths.txt")==evidence["routes_sha256"]
    installed=list(g.path_records(a.locked/"paths.txt"))
    owners={i:o for i,o,t,pin in plan["jobs"]}
    if a.mode=="merge":
        new=g.read(a.run/"plan.json")
        assert new["sites"][:len(plan["sites"])]==plan["sites"]
        with (a.run/"paths.txt").open("x") as out:
            for i,t,path in installed:
                print(i,t,len(path),file=out)
                for row in path: print(*row,file=out)
            for i,t,path in g.path_records(a.run/"extra-paths.txt"):
                print(i,t+len(plan["sites"]),len(path),file=out)
                for row in path: print(*row,file=out)
        return
    locked_ids={i for i,_,_ in installed}
    occupied_targets={t for _,t,_ in installed}
    added=[]
    for i,target,path in installed:
        x,y,_,_,_=plan["sites"][target]
        pad=g.rect((x,y),(x,y),2000)
        added.extend(g.shapes_for(owners[i],path,pad,plan["area"],g.STEP))
    with (a.locked/"input.txt").open() as source:
        x0,y0,nx,ny,n=map(int,next(source).split())
        native=[next(source) for _ in range(n)]
    assert [x0,y0,nx,ny]==plan["mesh"]
    sites=[entry for i,entry in enumerate(plan["sites"]) if i not in occupied_targets
           and not g.too_close(g.rect(entry[:2],entry[:2],2000),AREA,12000)]
    jobs=[]
    for i,o,terminal,pin in plan["jobs"]:
        x=(terminal[0]+terminal[2])//2
        y=(terminal[1]+terminal[3])//2
        if i not in locked_ids and AREA[0]<x<AREA[2] and AREA[1]<y<AREA[3]:
            jobs.append((i,o,terminal,pin))
    assert len(jobs)>=30
    with (a.run/"input.txt").open("x") as out:
        print(x0,y0,nx,ny,n+len(added),file=out)
        out.writelines(native)
        for owner,layer,rc in added: print(owner,layer,*rc,file=out)
        print(len(sites),file=out)
        for row in sites: print(*row,file=out)
        print(len(jobs),file=out)
        for i,o,terminal,pin in jobs: print(i,o,*terminal,file=out)
    plan["sites"]+=sites
    g.write(a.run/"plan.json",plan)
    print("C0 local cut candidates",len(jobs),"alternative sites",len(sites),flush=True)


if __name__=="__main__":
    main()
