"""Measure full M1-M10 interface charge, including the shared M10 landing.

This is a second accounting view of identical physical geometry. The main
upper comparison follows PR216 (upper owns the landing); this diagnostic
follows the macro definition (M1-M10 owns it). Never add the two views.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

from native_shared_reference import HEADER, RECORD, UPPER, sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scene',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--shared-reference',type=Path,required=True)
    p.add_argument('--masters',required=True)
    p.add_argument('--offset',type=float,default=.25)
    p.add_argument('--walks',type=int,default=1048576)
    a=p.parse_args();meta=json.loads((a.scene/'scene.json').read_text())
    assert meta['complete_native_instance_context'] and meta['minimum_native_layer']==1
    assert sha(UPPER)==meta['source_upper_sha256']
    upper=json.loads(UPPER.read_text())
    out=Path(os.environ['COUPLING_OUT'])/'result';out.mkdir()
    original=a.scene/'scene.bin';assert sha(original)==meta['scene_sha256']
    lower=a.scene/'lower-only.bin';assert sha(lower)==meta['lower_scene_sha256']
    landing=json.loads((a.shared_reference/'lower-reference.json').read_text())
    assert landing['parent_scene_metadata_sha256']==sha(a.scene/'scene.json')
    assert landing['original_native_scene_sha256']==meta['lower_scene_sha256']
    landing_file=a.shared_reference/'lower-only.bin'
    assert sha(landing_file)==landing['reference_scene_sha256']
    expected={i:sum((b[3]-b[0])*(b[4]-b[1])*(b[5]-b[2]) for b in r['boxes']
                    if b[5]<=12.09+1e-10) for i,r in enumerate(upper)}
    covered={i:0. for i in expected}
    with landing_file.open('rb') as f:
        f.seek(-RECORD.size*landing['added_shared_boxes'],2)
        for row in RECORD.iter_unpack(f.read()):
            assert row[1]==0
            covered[row[0]]+=(row[5]-row[2])*(row[6]-row[3])*(row[7]-row[4])
    assert all(expected[i]>0 and abs(covered[i]-expected[i])<1e-7*expected[i] for i in expected), 'Upper landing is not entirely preexisting native metal'
    modified=out/'macro-owned-m10.bin';assert not modified.exists()
    shutil.copyfile(original,modified)
    changed=0
    with modified.open('r+b') as f:
        magic,nets,count,eps=HEADER.unpack(f.read(HEADER.size));assert magic==b'NATIVE22'
        for _ in range(nets):
            length=struct.unpack('<I',f.read(4))[0];f.read(length+1)
        for i,record in enumerate(upper):
            for box in record['boxes']:
                position=f.tell();row=RECORD.unpack(f.read(RECORD.size))
                assert row[:2]==(i,0) and row[2:]==tuple(box),'Upper prefix changed'
                if box[5]<=12.09+1e-10:
                    assert box[2]>=10.09-1e-10
                    f.seek(position+4);f.write(struct.pack('<i',1));f.seek(position+RECORD.size)
                    changed+=1
                else:assert box[2]>=12.09-1e-10,'Conductor straddles ownership boundary'
    assert changed
    ids=[int(i) for i in a.masters.split(',')]
    assert len(ids)==len(set(ids)) and all(0<=i<2491 for i in ids)
    masters=out/'masters.txt';masters.write_text('\n'.join(map(str,ids))+'\n')
    build=json.loads((a.build/'build.json').read_text());binary=a.build/'native_field'
    assert build.get('bidirectional_interval_merge')
    assert sha(binary)==build['binary_sha256']
    proof=json.loads((a.build.parent/'controls/controls.json').read_text())
    assert proof['passed'] and proof['exact_match_unoptimized_controls']
    rows={}
    for label,scene in [('without-upper',lower),('with-upper',modified)]:
        target=out/(label+'.jsonl')
        with target.open('xb') as stdout,(out/(label+'.log')).open('xb') as stderr:
            subprocess.run([str(binary),str(scene),str(masters),os.environ['COUPLING_THREADS'],
                            str(a.walks),str(a.offset),'104729'],stdout=stdout,stderr=stderr,check=True)
        rows[label]={}
        with target.open() as f:
            for line in f:
                row=json.loads(line);i=row['master'];assert i not in rows[label]
                assert abs(sum(v[0] for v in row['values']))<1e-8*row['total_ff']
                rows[label][i]=row
        assert list(rows[label])==ids
    comparison=[]
    for i in ids:
        before=rows['without-upper'][i];after=rows['with-upper'][i]
        original_cap=before['total_ff'];new_cap=after['values'][i][4]
        assert abs(before['values'][i][2])<1e-10,'Native reference has non-native source charge'
        comparison.append(dict(net=before['net'],native_m1_m10_without_upper_ff=original_cap,
                native_m1_m10_with_upper_ff=new_cap,delta_ff=new_cap-original_cap,
                delta_percent=100*(new_cap/original_cap-1),
                conservative_95ci_halfwidth_ff=2*(before['sigma_ff']+after['values'][i][5]),
                combined_conductor_ff=after['total_ff'],upper_above_m10_ff=after['values'][i][2]))
    report=dict(nets=len(ids),full_upper_coverage=(len(ids)==2491),
                complete_native_instance_context=True,minimum_native_layer=1,offset=a.offset,
                macro_includes_shared_m10=True,changed_ownership_boxes=changed,
                upper_m10_entirely_preexisting_native=True,
                maximum_landing_volume_error_um3=max(abs(covered[i]-expected[i]) for i in expected),
                conductor_geometry_unchanged=True,original_scene_sha256=meta['scene_sha256'],
                source_scene_metadata_sha256=sha(a.scene/'scene.json'),
                macro_accounting_scene_sha256=sha(modified),solver_sha256=build['binary_sha256'],
                surface_interval_merge_fixed=True,
                all_total_statistical_gates=all(r['sigma_ff']<=.003*r['total_ff'] for v in rows.values() for r in v.values()),
                direct_macro_reuse_qualified=False,
                scope='Full M1-M10 interface conductor charge under quiet other signals. Internal-net capacitances, original macro timing arcs and distributed RC remain separate.',
                accounting='Diagnostic view gives all M10 to macro. Main PR216-compatible upper comparison includes its M10 landing. Do not sum these different accounting views.')
    (out/'macro-boundary.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'macro-boundary-nets.json').write_text(json.dumps(comparison,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
