import argparse
import json
import os
from pathlib import Path
import subprocess
from vectors import generate


def main(args):
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=10
    args.out.mkdir(parents=True,exist_ok=False)
    exp=args.source/'project/experiments/native_s32_dot'
    report=generate(args.out,args.seed,exp/'reference/qwen25-attention.json')
    report.update(passed=False,job=os.environ['SLURM_JOB_ID'],affinity=sorted(os.sched_getaffinity(0)))
    try:
        build=args.out/'obj-core'
        command=['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator',
          '--binary','--timing','--assert','--Wall','--x-initial','unique','--x-assign','unique',
          '-Wno-BLKSEQ','--top-module','tb_core','--Mdir',str(build),'-j','10',
          str(exp/'tb_core.sv'),str(args.source/'project/rtl/native_s32_dot/dot_s32_core.sv')]
        with (args.out/'build.log').open('w') as log:
            subprocess.run(command,check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        for initial in range(3):
            with (args.out/f'core-{initial}.log').open('w') as log:
                subprocess.run([str(build/'Vtb_core'),'+vectors='+str(args.out/'core.txt'),
                  '+verilator+seed+'+str(args.seed),'+verilator+rand+reset+'+str(initial)],
                  check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        report['passed']=True
    finally:(args.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--seed',type=int,required=True)
    main(p.parse_args())
