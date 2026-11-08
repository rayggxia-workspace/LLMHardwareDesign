"""Extract paired local native capacitance, expanding insufficient windows."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import time

MASTER=struct.Struct('<I6dQd')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tiles',type=Path,required=True);p.add_argument('--build',type=Path,required=True)
    p.add_argument('--shards',type=int,default=32);p.add_argument('--masters');p.add_argument('--offset',type=float,default=.5)
    p.add_argument('--margin',type=float,default=32.);p.add_argument('--max-margin',type=float,default=256.)
    p.add_argument('--walks',type=int,default=16384);p.add_argument('--seed',type=int,default=104729)
    a=p.parse_args();out=Path(os.environ['LOWER_OUT']);out.mkdir();start=time.monotonic()
    prep=json.loads((a.tiles/'prepare.json').read_text());build=json.loads((a.build/'build.json').read_text())
    assert prep['all_tile_files_hash_verified'] and build['all_golden_controls_passed']
    geometry=Path(prep['geometry']);assert sha(geometry/'masters.bin')==prep['masters_sha256']
    assert sha(geometry/'runtime.txt')==prep['runtime_sha256']
    binary=Path(build['binaries']['lower_local_field']['path']);assert sha(binary)==build['binaries']['lower_local_field']['sha256']
    index=int(os.environ.get('LOWER_INDEX','0'));assert 0<=index<a.shards
    requested=set(map(int,a.masters.split(','))) if a.masters else None
    selected=[];seen=set()
    with (geometry/'masters.bin').open('rb') as source,(out/'masters.bin').open('xb') as target:
        while True:
            raw=source.read(MASTER.size)
            if not raw:break
            assert len(raw)==MASTER.size;master=MASTER.unpack(raw)[0]
            if (requested is not None and master in requested) or (requested is None and master%a.shards==index):
                assert master not in seen;seen.add(master);selected.append(master);target.write(raw)
    assert selected and (requested is None or seen==requested)
    rows=out/'native-pairs.jsonl';command=[str(binary),str(geometry),str(out/'masters.bin'),os.environ['LOWER_CPUS'],str(a.walks),str(a.offset),str(a.margin),str(a.max_margin),str(a.seed),'.002']
    with rows.open('xb') as stdout,(out/'field.log').open('xb') as stderr:subprocess.run(command,stdout=stdout,stderr=stderr,check=True)
    ids=[];unqualified=[]
    with rows.open() as f:
        for line in f:
            row=json.loads(line);ids.append(row['master']);assert row['before_ff']>0 and row['after_ff']>0
            if not row['qualified']:unqualified.append(row['master'])
    assert ids==selected
    report=dict(tile_preparation=str(a.tiles),tile_preparation_sha256=sha(a.tiles/'prepare.json'),
        build=str(a.build),build_metadata_sha256=sha(a.build/'build.json'),binary_sha256=sha(binary),
        rows_sha256=sha(rows),rows_bytes=rows.stat().st_size,masters=selected,shard=index,shards=a.shards,
        offset=a.offset,initial_margin_um=a.margin,maximum_margin_um=a.max_margin,minimum_walks=a.walks,
        seed=a.seed,unqualified_masters=unqualified,all_local_gates_passed=not unqualified,elapsed_seconds=time.monotonic()-start,
        original_native_geometry_and_resistance_unchanged=True,
        scope='Paired metal-only C. Same physical geometry, local windows adapt using existing solver leakage estimate, quiet other signals. Device C and node-resolved timing remain separate.')
    (out/'local-solve.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='masters'}),flush=True)

if __name__=='__main__':main()
