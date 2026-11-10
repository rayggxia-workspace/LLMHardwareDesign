import argparse
import json
import os
from pathlib import Path
import subprocess


def main(args):
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0)) <= 10
    args.out.mkdir(parents=True, exist_ok=False)
    exp = args.source / 'project/experiments/native_s32_dot'
    upstream = args.source.parent / 'upstream'
    obj = args.out / 'obj-stage64'
    report = dict(passed=False, job=os.environ['SLURM_JOB_ID'], seed=args.seed,
                  affinity=sorted(os.sched_getaffinity(0)), real_S=True, tests=[])
    build = ['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator', '--binary', '--timing',
             '--assert', '--Wall', '--x-initial', 'unique', '--x-assign', 'unique', '-Wno-BLKSEQ',
             '--top-module', 'tb_stage64', '--Mdir', str(obj), '-j', '10', str(exp / 'tb_stage64.sv'),
             str(args.source / 'project/rtl/native_s32_dot/dot_s32_stage64.sv'), '--timescale-override',
             '1ns/1ps', str(exp / 's128_lint.vlt'), str(upstream / 'local_s_base.sv'),
             str(upstream / 'block_feed_s16k_sram.sv'), str(upstream / 's_sram_256x128_freepdk45.v')]
    try:
        with (args.out / 'build.log').open('w') as log:
            subprocess.run(build, check=True, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        for mode in range(2):
            for initial in range(3):
                name = f'stage64-{mode}-{initial}'
                with (args.out / f'{name}.log').open('w') as log:
                    subprocess.run([str(obj / 'Vtb_stage64'), '+trace=' + str(args.out / f'timing-{mode}-{initial}.csv'),
                                    f'+mode={mode}', f'+verilator+seed+{args.seed}', f'+verilator+rand+reset+{initial}'],
                                   check=True, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                report['tests'].append(dict(mode=mode, initial=initial, log=f'{name}.log'))
        report['passed'] = True
    finally:
        (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--seed', required=True, type=int)
    main(parser.parse_args())
