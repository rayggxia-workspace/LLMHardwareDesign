"""Solve only requested rows of a hash-pinned prepared native context."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda:stream.read(4 << 20),b''):h.update(b)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scene',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--masters',required=True)
    p.add_argument('--offset',type=float,default=.25)
    p.add_argument('--walks',type=int,default=262144)
    p.add_argument('--lower-only',action='store_true')
    p.add_argument('--lower-reference',type=Path)
    a=p.parse_args()
    if a.masters.startswith('shard:'):
        shards=int(a.masters.split(':')[1]);shard=int(os.environ['COUPLING_SHARD'])
        assert 0<=shard<shards<=2491
        ids=list(range(shard,2491,shards))
    else:
        ids=[int(x) for x in a.masters.split(',')]
    assert ids and len(ids)==len(set(ids)) and all(0<=x<2491 for x in ids)
    assert a.offset>0 and a.walks>=16384
    meta=json.loads((a.scene/'scene.json').read_text())
    scene=a.scene/('lower-only.bin' if a.lower_only else 'scene.bin')
    shared_reference=None
    if a.lower_reference:
        assert a.lower_only
        shared_reference=json.loads((a.lower_reference/'lower-reference.json').read_text())
        assert shared_reference['parent_scene_metadata_sha256']==sha(a.scene/'scene.json')
        assert shared_reference['original_native_scene_sha256']==meta['lower_scene_sha256']
        assert shared_reference['conductor_union_unchanged']
        assert shared_reference['owner_partition']=='upper_including_shared_m10_else_native'
        scene=a.lower_reference/'lower-only.bin'
        assert sha(scene)==shared_reference['reference_scene_sha256']
    else:
        assert not a.lower_only,'Lower-only comparison requires consistent shared-interface ownership'
        assert sha(scene)==meta['scene_sha256']
    build=json.loads((a.build/'build.json').read_text())
    assert build.get('bidirectional_interval_merge'), 'Native scenes require the separated-box merge fix'
    solver=a.build/'native_field'
    assert sha(solver)==build['binary_sha256']
    controls=json.loads((a.build.parent/'controls/controls.json').read_text())
    assert controls['passed'] and controls['exact_match_unoptimized_controls']
    out=Path(os.environ['COUPLING_OUT'])/'result'
    out.mkdir()
    (out/'masters.txt').write_text('\n'.join(map(str,ids))+'\n')
    command=[str(solver),str(scene),str(out/'masters.txt'),os.environ['COUPLING_THREADS'],
             str(a.walks),str(a.offset),'104729']
    with (out/'rows.jsonl').open('xb') as stdout,(out/'field.log').open('xb') as stderr:
        subprocess.run(command,stdout=stdout,stderr=stderr,check=True)
    rows=[json.loads(line) for line in (out/'rows.jsonl').read_text().splitlines()]
    assert [row['master'] for row in rows]==ids
    for row in rows:
        values=row['values'];total=row['total_ff']
        assert total>0 and values[row['master']][0]==total
        assert abs(sum(v[0] for v in values))<=1e-8*total
    result=dict(passed=True,scene_sha256=sha(scene),scene_metadata_sha256=sha(a.scene/'scene.json'),
                solver_sha256=build['binary_sha256'],masters=ids,offset=a.offset,minimum_walks=a.walks,
                surface_interval_merge_fixed=True,
                lower_only=a.lower_only,rows_sha256=sha(out/'rows.jsonl'),
                owner_partition='upper_including_shared_m10_else_native',
                lower_reference_sha256=sha(a.lower_reference/'lower-reference.json') if shared_reference else None,
                complete_native_instance_context=meta['complete_native_instance_context'],
                minimum_native_layer=meta['minimum_native_layer'],
                maximum_relative_standard_error=max(r['sigma_ff']/r['total_ff'] for r in rows),
                all_rows_statistical_gate=all(r['sigma_ff']<=.003*r['total_ff'] for r in rows),
                scope='Requested Maxwell rows only; local charge, depth/offset convergence and macro timing qualification are separate.')
    (out/'solve.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
