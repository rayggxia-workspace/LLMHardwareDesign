"""Recheck and, where needed, extend only the admitted 1184-net M10 fanouts."""
import csv
import gzip
from collections import Counter, defaultdict
from pathlib import Path
import sys

import lower_rules as geo


ROOT=Path.cwd()
PARENT=ROOT.parent
PRE=ROOT/'precheck-first'
OLD=PARENT/'hpy-pr276-multiblock.vqYobQqC'
RELIEF=PARENT/'hpy-pr276-split.DaN7C6dX/u0-relief.H2MIrzpa'
PLACEMENT=PARENT/'hpy-pr271-top-hsVf4b/inputs/placement.json'
BLOCK_TYPES={'U0':'U.Gather','C0':'C','P0':'P','P1':'P','P2':'P','mc':'MC','sw':'SW'}


def rows(path, jobs, admitted):
    with path.open() as src:
        for line in src:
            i,t,n=map(int,line.split())
            pin=jobs[i][2]
            if pin not in admitted:
                for _ in range(n): next(src)
                continue
            yield i,t,[tuple(map(int,next(src).split())) for _ in range(n)]


def offset_shapes(path,xy,area):
    op=gzip.open if path.suffix=='.gz' else open
    shapes=[]; ports=defaultdict(set)
    with op(str(path),'rt') as f:
        assert 'dbu_per_um=2000' in next(f)
        x,y=xy
        for line in f:
            if line.startswith('#'): continue
            tag,layer,kind,*r=line.rstrip().split('\t')
            a,b,c,d=map(int,r)
            box=(a+x,b+y,c+x,d+y)
            if not geo.too_close(box,area,3000): continue
            owner=int(tag[1:]) if tag.startswith('n') and tag[1:].isdigit() and not kind.endswith('obs') else -1
            shapes.append((owner,geo.LAYERS[layer],box))
            if layer=='metal10' and kind=='block-port': ports[box].add(owner)
    return shapes,ports


def info(block,overlay):
    if block=='sw':
        replay=[(PARENT/'hpy-pr276-escape.EaL1oAqq/lower-p2.BLaJsN66','old-sw'),
                (OLD/'switch-wide.6u9tYIpS','wide-sw')]
        src=PARENT/'hpy-pr276-more-escape.wTRlKfO9/native-sw-full.tsv'
    else:
        replay=[(Path(overlay['modules'][block]['source']),'regular')]
        if block=='U0': replay.append((RELIEF,'extra-u0'))
        log,=OLD.glob('native-'+BLOCK_TYPES[block]+'-*.log')
        src=Path(next(x[4:] for x in log.read_text().splitlines() if x.startswith('run=')))/'native.tsv.gz'
    area_info=geo.read(replay[1 if block=='sw' else 0][0]/'plan.json')
    return replay,src,area_info


def convert_plan(folder,kind):
    if kind=='old-sw':
        plan=geo.read(folder/'lower-plan.json')
        return plan, folder/'lower-paths.txt',plan['targets'],3200,2
    plan=geo.read(folder/'plan.json')
    return plan,folder/'paths.txt',plan['sites'],geo.STEP,0


def main():
    mode,block,out=sys.argv[1:]; out=Path(out)
    s=geo.read(PRE/'derived-spec.json'); overlay=geo.read(PRE/'lower-evidence.json'); floor=geo.read(PLACEMENT)
    assert len(s['nets'])==1184 and geo.sha(PLACEMENT)==geo.PLACEMENT_SHA==overlay['placement_sha256']
    active={p for n in s['nets'] for p in (n['driver'],*n['sinks'])}
    admitted={r['pin']:r for r in overlay['rebound'] if r['pin'].split('/')[0]==block}
    assert set(admitted)<=active
    replay,src,plan=info(block,overlay)
    area=plan['area']; box=floor['boxes_dbu'][block]
    fixed,ports=offset_shapes(src,floor['placement_dbu'][block],area)
    check=geo.Checker(fixed)
    last_sources={}
    for folder,kind in replay:
        old,paths,sites,step,offset=convert_plan(folder,kind)
        jobs={i:(o,tuple(b),pin) for i,o,b,pin in old['jobs']}
        for i,t,path in rows(paths,jobs,admitted):
            owner,terminal,pin=jobs[i]
            x,y,*_=sites[t]; pad=geo.rect((x,y),(x,y),2000)
            row=admitted[pin]
            assert row['native_owner']==owner and row['new_m10']==list(pad)
            assert ports[terminal]=={owner} and row['old_m10']==list(terminal)
            path=[(a,b,c+offset) for a,b,c in path]
            assert path[0][2]==path[-1][2]==3
            assert geo.contains(terminal,geo.rect(path[0],path[0],800)) and geo.contains(pad,geo.rect(path[-1],path[-1],800))
            shapes=geo.shapes_for(owner,path,pad,old['area'],step)
            for o,l,r in shapes: check.verify(o,l,r)
            for o,l,r in shapes: check.add(o,l,r)
            fixed.extend(shapes)
            assert pin not in last_sources
            last_sources[pin]=owner
    assert set(last_sources)==set(admitted)

    oldfile=PARENT/'hpy-pr276-toponly.rPq68zlF/causes.m5Ba0Tql/causes.tsv'
    old_fail={int(r['index']):r['after'] for r in csv.DictReader(oldfile.open(),delimiter='\t') if r['after'] in ('driver_access','sink_access')}
    selected=[]
    for a in csv.DictReader((PRE/'access.tsv').open(),delimiter='\t'):
        i,j=int(a['net_index']),int(a['pin_index']); n=s['nets'][i]
        pin=([n['driver']]+n['sinks'])[j]
        if pin.split('/')[0]!=block: continue
        exits,near,reserved=(int(a[k]) for k in ('independent_exits','nearby_pins','reserved_exit'))
        previous=(j==0 and old_fail.get(i)=='driver_access') or (j>0 and old_fail.get(i)=='sink_access')
        if not (exits==0 or (previous and exits<=2 and near>=3) or (exits<=2 and near>=8 and not reserved)):
            continue
        terminal,=s['pins'][pin]; terminal=tuple(terminal)
        owner=last_sources[pin] if pin in last_sources else next(iter(ports[terminal]),-1)
        if owner<0 or (pin not in admitted and ports[terminal]!={owner}):
            raise RuntimeError('Cannot prove M10 owner for '+pin)
        selected.append((not previous,exits,-near,i,pin,owner,terminal))
    selected.sort()
    sites=[]; seen_sites=set()
    current=[tuple(r) for pin in active for r in s['pins'][pin]]
    for row in plan['sites']:
        x,y,ex,ey=row[:4]; pad=geo.rect((x,y),(x,y),2000)
        if any(geo.too_close(pad,b,6500) for b in current): continue
        if not geo.contains(area,pad) or geo.too_close(pad,box,0): continue
        if (ex,ey) in seen_sites: continue
        seen_sites.add((ex,ey))
        side=max(range(4),key=(box[0]-x,x-box[2],box[1]-y,y-box[3]).__getitem__)
        sites.append((x,y,ex,ey,side))
    jobs={k:v for k,v in enumerate(selected,1)}
    receipt={'block':block,'checked_old_paths':len(last_sources),'source_archive_sha256':geo.sha(src),
             'selected':len(selected),'layout_sha256':geo.sha(PLACEMENT),'paths':[]}
    if mode=='prepare':
        with (out/'input.txt').open('w') as stream:
            print(*plan['mesh'],len(fixed),file=stream)
            for o,l,r in fixed: print(o,l,*r,file=stream)
            print(len(sites),file=stream)
            for site in sites: print(*site,file=stream)
            print(len(jobs),file=stream)
            for k,(_,_,_,_,_,o,b) in jobs.items(): print(k,o,*b,file=stream)
        print('fanout',block,'old checked',len(last_sources),'candidates',len(jobs),'sites',len(sites),flush=True)
        return
    seen=set()
    for i,t,path in geo.path_records(out/'paths.txt'):
        prev,_,_,n,pin,owner,from_pad=jobs[i]
        assert i not in seen; seen.add(i)
        x,y,ex,ey,side=sites[t]; to_pad=geo.rect((x,y),(x,y),2000)
        assert path[0][2]==3 and path[-1]==(ex,ey,3)
        assert geo.contains(from_pad,geo.rect(path[0],path[0],800)) and geo.contains(to_pad,geo.rect(path[-1],path[-1],800))
        shapes=geo.shapes_for(owner,path,to_pad,area,geo.STEP)
        for o,l,r in shapes: check.verify(o,l,r)
        for o,l,r in shapes: check.add(o,l,r)
        receipt['paths'].append({'net':s['nets'][n]['id'],'pin':pin,'native_owner':owner,'block':block,
                                'old_m10':admitted[pin]['old_m10'] if pin in admitted else list(from_pad),
                                'new_m10':list(to_pad),'extension_from':list(from_pad),'prior_access_failure':not prev,
                                'landing_side':('west','east','south','north')[side]})
    receipt['paths_sha256']=geo.sha(out/'paths.txt')
    receipt['unmoved']=[{'pin':v[4],'previous_access_failure':not v[0]} for k,v in jobs.items() if k not in seen]
    geo.write(out/'fanout-verified.json',receipt)
    print('fanout_verified',block,'new',len(seen),'previous access-failure endpoints',sum(p['prior_access_failure'] for p in receipt['paths']),flush=True)


if __name__=='__main__': main()
