"""Calibrate native K32/N8 tiles using real operands and matched idle states.

This changes a software recipe, not DP or the accepted hardware netlist.
Numerical checks independently reconstruct S32 and all eight Python dots.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import sys
from m_streams import sha, call
import subprocess


def main():
    p=argparse.ArgumentParser()
    for name in ('compiled_model','model_manifest','verilator_include','operands','physical','liberty','output'):
        p.add_argument(name,type=Path)
    p.add_argument('--workers',type=int,default=6)
    p.add_argument('--cores-per-power',type=int,default=10)
    p.add_argument('--narrow-correction',action='store_true',
                   help='encode the exact 0/1 correction component using native S8 A')
    a=p.parse_args()
    import os
    if min(a.workers,a.cores_per_power)<1:
        raise ValueError('positive resources required')
    if os.environ.get('SLURM_NTASKS') and a.workers*a.cores_per_power>int(os.environ['SLURM_NTASKS'])*int(os.environ['SLURM_CPUS_PER_TASK']):
        raise ValueError('allocation exceeded')
    a.output.mkdir(exist_ok=False)
    manifest=json.loads(a.model_manifest.read_text())
    for name,digest in manifest['files_sha256'].items():
        if Path(name).name!=name or sha(a.compiled_model/name)!=digest:
            raise ValueError('compiled model drift')
    if sha(a.physical/'6_final.v')!=manifest['source_gate_v_sha256']:
        raise ValueError('physical/model netlist mismatch')
    source=Path(__file__).parent; binary=a.output/'m-tile'
    command=['g++','-std=c++17','-O1','-DVM_TRACE=1','-DVM_TRACE_VCD=1','-DVM_TRACE_FST=0',
             '-DVM_TRACE_SAIF=0','-DVM_TIMING=0','-DVM_COVERAGE=0',
             '-I'+str(a.compiled_model),'-I'+str(a.verilator_include),'-I'+str(a.verilator_include/'vltstd'),
             source/'m_activity.cpp',a.compiled_model/'Vblock_v2_m__ALL.a']
    command += [a.compiled_model/x for x in ('verilated.o','verilated_vcd_c.o','verilated_threads.o')]
    command += ['-pthread','-latomic','-o',binary]
    call(command,a.output/'build.log')
    capture=json.loads((a.operands/'receipt.json').read_text())
    tiles=capture['packed_tiles']
    if len(tiles)!=3 or sorted(x['cohort'] for x in tiles)!=[0,1,2]:
        raise ValueError('expected three captured cohorts')
    def worker(item):
        tile,mode=item; path=a.operands/tile['file']
        if Path(tile['file']).name!=tile['file'] or sha(path)!=tile['sha256']:
            raise ValueError('operand tile drift')
        rows=[list(map(int,x.split())) for x in path.read_text().splitlines()]
        if len(rows)!=768 or any(len(x)!=3 for x in rows):
            raise ValueError('expected complete K32/N8/three components')
        expected=[0]*8
        for k in range(32):
            for n in range(8):
                low,hi,flag=rows[(k*8+n)*3:(k*8+n)*3+3]
                if [low[2],hi[2],flag[2]]!=[0,16,16] or not low[1]==hi[1]==flag[1] or flag[0]!=int(low[0]<0):
                    raise ValueError('invalid S32 encoding')
                if [low[0],hi[0],flag[0]] != [rows[k*24+i][0] for i in range(3)]:
                    raise ValueError('A must be shared across output columns')
                expected[n]+=((low[0]&65535)+(hi[0]<<16))*low[1]
        out=a.output/('cohort-%d-%s'%(tile['cohort'],mode)); out.mkdir()
        call([binary,path,out/'gate.vcd',mode],out/'functional.log')
        events=[json.loads(x[9:]) for x in (out/'functional.log').read_text().splitlines() if x.startswith('ACTIVITY ')]
        if len(events)!=1 or not events[0]['passed'] or events[0]['s64_prefixes']!=expected:
            raise ValueError('independent eight-output integer check failed')
        active_cycles=149 if a.narrow_correction else 173
        execute_cycles=[49,49,25 if a.narrow_correction else 49]
        if events[0]['execute_cycles']!=execute_cycles or events[0]['cycles']!=(256 if mode.endswith('idle') else active_cycles):
            raise ValueError('native timing changed')
        functional=out/'functional.json'; functional.write_text(json.dumps({'timing':events[0]})+'\n')
        call([sys.executable,source/'analyze_activity.py',a.physical,a.liberty,out/'gate.vcd',functional,
              out/'power','--cores',a.cores_per_power],out/'analysis.log')
        return {'cohort':tile['cohort'],'mode':mode,'timing':events[0],
                'operand_sha256':tile['sha256'],'power':json.loads((out/'power/receipt.json').read_text())}
    modes=('tile-narrow','tile-narrow-idle') if a.narrow_correction else ('tile','tile-idle')
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        records=list(pool.map(worker,[(t,m) for t in tiles for m in modes]))
    pairs=[]
    for c in range(3):
        active,idle=[next(r for r in records if r['cohort']==c and r['mode']==m) for m in modes]
        delta=active['power']['power_w']['total']-idle['power']['power_w']['total']
        pairs.append({'cohort':c,'incremental_tile_j':delta*active['timing']['window_ps']*1e-12})
    receipt={'scope':'sampled real K32 N8 S32-by-S16 native tiles; not full-model timing/energy',
             'independent_s32_numeric_passed':True,'records':records,'active_idle_pairs':pairs,
             'narrow_correction':a.narrow_correction,
             'precision_changed':False,'hardware_changed':False,'dp_algorithm_changed':False,
             'driver_sha256':sha(source/'m_activity.cpp'),'runner_sha256':sha(Path(__file__)),
             'compiled_model_manifest_sha256':sha(a.model_manifest),'binary_sha256':sha(binary),
             'capture_receipt_sha256':sha(a.operands/'receipt.json'),
             'build_command':list(map(str,command)),
             'full_model_timing_qualified':False,'full_model_energy_qualified':False}
    (a.output/'summary.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'numeric_passed':True,'calibrated_pairs':len(pairs),'full_model_energy_qualified':False}))

if __name__=='__main__':
    main()
