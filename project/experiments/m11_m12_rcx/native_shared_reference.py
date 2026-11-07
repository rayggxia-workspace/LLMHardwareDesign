"""Keep shared M10 ownership consistent when removing only upper conductors.

The reference copies the exact native-only scene, then labels intersections
with original upper boxes as owner zero. Added boxes lie entirely inside
existing same-net native metal: they change ownership, never conductor union.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct

RECORD=struct.Struct('<ii6d')
HEADER=struct.Struct('<8sIQd')
UPPER=Path('/public/home/yuzelu/PingyangHuang/issue-215-top-pex-zOz2uxIr/job-99157/result/conductors.json')


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8<<20),b''):h.update(block)
    return h.hexdigest()


def cells(box):
    for x in range(math.floor(box[0]/16),math.floor(box[3]/16)+1):
        for y in range(math.floor(box[1]/16),math.floor(box[4]/16)+1):
            yield x,y


def shared(native, candidates):
    for net,upper in candidates:
        box=[max(native[k+2],upper[k]) for k in range(3)]+[
             min(native[k+5],upper[k+3]) for k in range(3)]
        if all(box[k+3]-box[k]>1e-10 for k in range(3)):
            assert net==native[0],('Different nets overlap at shared interface',net,native[0],box)
            yield net,tuple(box)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scene',type=Path,required=True)
    a=p.parse_args();meta=json.loads((a.scene/'scene.json').read_text())
    source=a.scene/'lower-only.bin'
    assert sha(source)==meta['lower_scene_sha256']
    assert sha(UPPER)==meta['source_upper_sha256']
    upper=json.loads(UPPER.read_text());lookup={}
    for i,row in enumerate(upper):
        for box in row['boxes']:
            if box[2]<12.09-1e-8 and box[5]>10.09+1e-8:
                for cell in cells(box):lookup.setdefault(cell,[]).append((i,box))
    pieces=set();native_boxes=0
    with source.open('rb') as f:
        magic,nets,count,eps=HEADER.unpack(f.read(HEADER.size));assert magic==b'NATIVE22'
        for _ in range(nets):
            length=struct.unpack('<I',f.read(4))[0];f.read(length+1)
        while True:
            data=f.read(RECORD.size*65536)
            if not data:break
            for row in RECORD.iter_unpack(data):
                native_boxes+=1
                assert row[1]==1,'Native-only scene unexpectedly contains upper ownership'
                if row[4]>=12.09-1e-8 or row[7]<=10.09+1e-8:continue
                candidates={}
                for cell in cells(row[2:]):
                    for net,box in lookup.get(cell,[]):candidates[(net,tuple(box))]=(net,box)
                pieces.update(shared(row,candidates.values()))
        assert native_boxes==count
    assert pieces,'No shared interface was found'
    out=Path(os.environ['COUPLING_OUT'])/'result';out.mkdir()
    target=out/'lower-only.bin'
    assert not target.exists();shutil.copyfile(source,target)
    with target.open('r+b') as f:
        f.seek(0,2)
        for net,box in sorted(pieces):f.write(RECORD.pack(net,0,*box))
        f.seek(12);f.write(struct.pack('<Q',count+len(pieces)))
    report=dict(parent_scene_metadata_sha256=sha(a.scene/'scene.json'),
                original_native_scene_sha256=sha(source),reference_scene_sha256=sha(target),
                owner_partition='upper_including_shared_m10_else_native',
                original_native_boxes=count,added_shared_boxes=len(pieces),
                shared_nets=len({n for n,_ in pieces}),
                conductor_union_unchanged=True,
                proof='Each added box is the positive-volume same-net intersection of an original upper box and an existing native box.',
                scope='Consistent ownership reference; not an additional extraction or a new physical conductor.')
    (out/'lower-reference.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
