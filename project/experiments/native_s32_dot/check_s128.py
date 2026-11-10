import argparse
import json
import os
from pathlib import Path
import subprocess
from vectors_s128 import generate


def main(args):
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=10
    args.out.mkdir(parents=True,exist_ok=False);exp=args.source/'project/experiments/native_s32_dot'
    real=os.environ.get('NATIVE32_REAL_S','0')=='1'
    report=dict(passed=False,job=os.environ['SLURM_JOB_ID'],seed=args.seed,
                affinity=sorted(os.sched_getaffinity(0)),real_s=real,variants=[])
    try:
        for rows in (1,2,4):
            current=args.out/f'rows-{rows}';current.mkdir()
            report['variants'].append(generate(current,args.seed,exp/'reference/qwen25-attention.json',rows))
            build=current/'obj-s128'
            command=['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator',
              '--binary','--timing','--assert','--Wall','--x-initial','unique','--x-assign','unique',
              '-Wno-BLKSEQ','--top-module','tb_s128','-GROWS='+str(rows),'--Mdir',str(build),'-j','10',
              str(exp/'tb_s128.sv'),str(args.source/'project/rtl/native_s32_dot/dot_s32_core.sv'),
              str(args.source/'project/rtl/native_s32_dot/dot_s32_s128.sv')]
            if real:
                upstream=args.source.parent/'upstream'
                command += ["-GREAL_S=1'b1",'--timescale-override','1ns/1ps',str(exp/'s128_lint.vlt'),
                            str(upstream/'local_s_base.sv'),str(upstream/'block_feed_s16k_sram.sv'),
                            str(upstream/'s_sram_256x128_freepdk45.v')]
            with (current/'build.log').open('w') as log:
                subprocess.run(command,check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            for initial in range(3):
                for mode in (0,1):
                    with (current/f'service-{mode}-{initial}.log').open('w') as log:
                        subprocess.run([str(build/'Vtb_s128'),'+vectors='+str(current/'service.txt'),
                          '+trace='+str(current/f'timing-{mode}-{initial}.csv'),'+mode='+str(mode),
                          '+verilator+seed+'+str(args.seed),'+verilator+rand+reset+'+str(initial)],
                          check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        report['passed']=True
    finally:(args.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--seed',type=int,required=True)
    main(p.parse_args())
