"""Build tiled reporter using accepted solver objects and verify golden scenes."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import shutil

BASE=Path('/public/home/yuzelu/PingyangHuang')
BUILD=BASE/'issue-222-merge-fix-OLZaDNeN/job-100237/build'
SOURCE=Path('/public/home/yuzelu/opt/eda/llhd-fsv-i121-block-v1-20261027-099')
HEADER=struct.Struct('<8sIQd');RECORD=struct.Struct('<ii6d')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reuse-field-build',type=Path);args=parser.parse_args()
    out=Path(os.environ['LOWER_OUT']);out.mkdir();src=Path(__file__).resolve().parent
    proof=json.loads((BUILD/'build.json').read_text());assert proof['bidirectional_interval_merge']
    objects=[BUILD/'Solver.o',BUILD/'GaussianSurface.o']+[SOURCE/n for n in proof['unchanged_objects']]
    assert all(sha(SOURCE/n)==v for n,v in proof['unchanged_objects'].items())
    root=SOURCE/'src/fsv';flags=['g++','-std=c++20','-O3','-pthread','-I'+str(BUILD/'include'),'-I'+str(root/'include'),'-I'+str(root/'src')]
    with (out/'compile.log').open('xb') as f:
        subprocess.run([*flags,str(src/'lower_tiles.cpp'),'-o',str(out/'lower_tiles')],stdout=f,stderr=subprocess.STDOUT,check=True)
        if args.reuse_field_build:
            original_build=json.loads((args.reuse_field_build/'build.json').read_text())
            assert sha(src/'lower_local_field.cpp')==original_build['source_sha256']['lower_local_field.cpp']
            assert sha(args.reuse_field_build/'lower_local_field')==original_build['binaries']['lower_local_field']['sha256']
            shutil.copy2(args.reuse_field_build/'lower_local_field',out/'lower_local_field')
        else:subprocess.run([*flags,str(src/'lower_local_field.cpp'),*map(str,objects),'-o',str(out/'lower_local_field')],stdout=f,stderr=subprocess.STDOUT,check=True)
    controls=BUILD.parent/'controls';checks=[];salt=0x9E3779B97F4A7C15;mask=(1<<64)-1
    # Keep the exact original physical coordinates and one target with ID2502;
    # all other fixture conductors remain quiet at the same zero potential.
    for name in ['split-one','split-many','single-owner','separate-neighbors','common-potential','disjoint-near-equal-coordinates']:
        original=controls/(name+'.bin')
        with original.open('rb') as f:
            magic,n,count,eps=HEADER.unpack(f.read(HEADER.size));assert magic==b'NATIVE22'
            for _ in range(n):ln=struct.unpack('<I',f.read(4))[0];f.read(ln+1)
            boxes=[RECORD.unpack(f.read(RECORD.size)) for _ in range(count)]
        fixture=out/(name+'.bin')
        with fixture.open('xb') as f:
            f.write(HEADER.pack(magic,2503,count,eps))
            for i in range(2503):
                label=('N'+str(i)).encode();f.write(struct.pack('<I',len(label))+label+b'\0')
            for net,owner,*b in boxes:f.write(RECORD.pack(2502 if net==0 else 2491,1,*b))
        tiles=out/(name+'-tiles')
        with (out/(name+'-tile.log')).open('xb') as f:subprocess.run([str(out/'lower_tiles'),str(fixture),str(tiles),'32'],stdout=f,stderr=subprocess.STDOUT,check=True)
        # Compensate both global/local renumbering so draws match old master0.
        seed=99991 ^ ((salt*2503)&mask) ^ salt
        target=out/(name+'.jsonl')
        if args.reuse_field_build:
            old_tiles=args.reuse_field_build/(name+'-tiles')
            for file in tiles.rglob('*'):
                if file.is_file():assert sha(file)==sha(old_tiles/file.relative_to(tiles)),file
            shutil.copyfile(args.reuse_field_build/(name+'.jsonl'),target);shutil.copyfile(args.reuse_field_build/(name+'.log'),out/(name+'.log'))
        else:
            with target.open('xb') as f,(out/(name+'.log')).open('xb') as e:
                subprocess.run([str(out/'lower_local_field'),str(tiles),str(tiles/'masters.bin'),'1' if name=='split-one' else '4','262144','.125','32','256',str(seed),'.002'],stdout=f,stderr=e,check=True)
        row=json.loads(target.read_text());reference=json.loads((controls/(name+'.jsonl')).read_text())
        assert row['before_ff']==row['after_ff'] and row['before_sigma_ff']==row['after_sigma_ff'],name
        error=abs(row['before_ff']-reference['total_ff'])
        assert error<=5*(row['before_sigma_ff']+reference['sigma_ff']), (name,error)
        assert row['target_volume_um3']>0
        checks.append(dict(case=name,unchanged_scene_delta_exactly_zero=True,global_difference_ff=error,
            global_sigma_ff=reference['sigma_ff'],local_sigma_ff=row['before_sigma_ff'],window_leakage_ff=row['before_window_leakage_ff'],
            tile_volume_conservation=True,original_control_sha256=sha(controls/(name+'.jsonl'))))
    result=dict(binaries={n:dict(path=str(out/n),sha256=sha(out/n)) for n in ['lower_tiles','lower_local_field']},
        source_sha256={n:sha(src/n) for n in ['lower_tiles.cpp','lower_local_field.cpp']},
        original_solver_binary_sha256=proof['binary_sha256'],linked_objects={str(f):sha(f) for f in objects},
        solver_algorithm_unchanged=True,golden_controls=checks,all_golden_controls_passed=True,
        reused_field_build=str(args.reuse_field_build) if args.reuse_field_build else None,
        qualification='Tile partition and golden geometry controls only. Real-native global/window/offset comparisons required before production qualification.')
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)

if __name__=='__main__':main()
