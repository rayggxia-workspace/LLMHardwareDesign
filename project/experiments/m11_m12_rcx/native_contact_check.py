"""Diagnose exact zero-clearance boxes without the solver's spatial index."""
import argparse
import bisect
import json
import os
from pathlib import Path

from native_shared_reference import HEADER, RECORD


def merged_boxes(boxes):
    boxes=[list(b) for b in boxes]
    changed=True
    while changed:
        changed=False
        for k in range(3):
            boxes.sort(key=lambda b:tuple(v for t in range(3) if t!=k for v in (b[t],b[t+3]))+(b[k],b[k+3]))
            merged=[]
            for b in boxes:
                last=merged[-1] if merged else None
                equal=last is not None and all(abs(last[t]-b[t])<=1e-9 and abs(last[t+3]-b[t+3])<=1e-9 for t in range(3) if t!=k)
                if equal and b[k]<=last[k+3]+1e-9:
                    merged[-1]=[min(last[t],b[t]) for t in range(3)]+[max(last[t+3],b[t+3]) for t in range(3)]
                else:merged.append(b)
            changed|=len(merged)<len(boxes);boxes=merged
        kept=[b for i,b in enumerate(boxes) if not any(i!=j and all(a[t]<=b[t] and a[t+3]>=b[t+3] for t in range(3)) for j,a in enumerate(boxes))]
        changed|=len(kept)<len(boxes);boxes=kept
    return boxes


def inspect(path,master):
    with path.open('rb') as f:
        magic,nets,count,eps=HEADER.unpack(f.read(HEADER.size));assert magic==b'NATIVE22'
        names=[]
        for _ in range(nets):
            n=int.from_bytes(f.read(4),'little');names.append(f.read(n).decode());f.read(1)
        rows=list(RECORD.iter_unpack(f.read()))
    assert len(rows)==count
    target=[(i,r) for i,r in enumerate(rows) if r[0]==master]
    target += [('merged-'+str(i),(master,-1,*b)) for i,b in enumerate(merged_boxes([r[2:] for _,r in target]))]
    ordered=sorted((r[2],i) for i,r in enumerate(rows) if r[0]!=master)
    xs=[x for x,_ in ordered];contacts=[]
    for i,a in target:
        stop=bisect.bisect_right(xs,a[5]+1e-8)
        for index in range(stop):
            _,j=ordered[index]
            b=rows[j]
            if b[5]+1e-8<a[2] or b[6]+1e-8<a[3] or b[3]>a[6]+1e-8 or b[7]+1e-8<a[4] or b[4]>a[7]+1e-8:continue
            contacts.append(dict(first=i,second=j,first_net=names[a[0]],second_net=names[b[0]],
                                 first_box=list(a),second_box=list(b),
                                 gap=max(max(a[k+2]-b[k+5],b[k+2]-a[k+5]) for k in range(3))))
    return dict(scene=str(path),boxes=count,master=master,master_boxes=len(target),contacts=contacts)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scenes',type=Path,nargs='+',required=True)
    p.add_argument('--master',type=int,required=True)
    a=p.parse_args();out=Path(os.environ['COUPLING_OUT'])/'result';out.mkdir()
    records=[inspect(scene,a.master) for scene in a.scenes]
    (out/'contacts.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps([dict(scene=r['scene'],master_boxes=r['master_boxes'],contacts=len(r['contacts'])) for r in records]))


if __name__=='__main__':main()
