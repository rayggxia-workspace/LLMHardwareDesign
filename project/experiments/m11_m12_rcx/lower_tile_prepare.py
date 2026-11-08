"""Partition a proven relabeled scene once for reusable bounded-window solves."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scene',type=Path,required=True);p.add_argument('--build',type=Path,required=True)
    p.add_argument('--tile-size',type=float,default=32.)
    a=p.parse_args();out=Path(os.environ['LOWER_OUT']);out.mkdir()
    meta=json.loads((a.scene/'scene.json').read_text());build=json.loads((a.build/'build.json').read_text())
    assert meta['exact_box_matches'] and meta['conductor_coordinates_order_and_ownership_unchanged']
    assert build['all_golden_controls_passed'] and build['solver_algorithm_unchanged']
    binary=Path(build['binaries']['lower_tiles']['path']);assert sha(binary)==build['binaries']['lower_tiles']['sha256']
    source=a.scene/'with-upper.bin';assert sha(source)==meta['files']['with-upper.bin']['sha256']
    target=out/'geometry'
    with (out/'tiles.log').open('xb') as f:subprocess.run([str(binary),str(source),str(target),str(a.tile_size)],stdout=f,stderr=subprocess.STDOUT,check=True)
    tm=json.loads((target/'tiles.json').read_text());assert tm['selected_electrodes']==meta['selected_electrodes']
    assert tm['omitted_duplicate_shared_m10_boxes']==4982 and tm['per_box_volume_conserved']
    index={}
    for f in sorted((target/'tiles').glob('*.bin')):index[f.name]=dict(bytes=f.stat().st_size,sha256=sha(f))
    assert len(index)==tm['tiles']
    (out/'tile-index.json').write_text(json.dumps(index,indent=2)+'\n')
    result=dict(source_scene=str(a.scene),source_scene_metadata_sha256=sha(a.scene/'scene.json'),source_scene_sha256=sha(source),
        tiler_sha256=sha(binary),tile_metadata=tm,geometry=str(target),tile_index_sha256=sha(out/'tile-index.json'),
        masters_sha256=sha(target/'masters.bin'),runtime_sha256=sha(target/'runtime.txt'),
        all_tile_files_hash_verified=True,scope='Exact tiling of existing conductor union, with only duplicate shared M10 boxes omitted. Local solve qualification remains separate.')
    (out/'prepare.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)

if __name__=='__main__':main()
