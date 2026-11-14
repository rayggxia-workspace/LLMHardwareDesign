"""Generate independent fixed-point Softmax stimuli and run on allocated Slurm cores."""
import argparse
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess


def rne(n, d):
    quotient, remainder = divmod(n, d)
    return quotient + (2*remainder>d or (2*remainder==d and quotient%2==1))


def coefficients():
    with localcontext() as context:
        context.prec=60
        return [int(((Decimal(i)/128-16).exp()*65536).to_integral_value(rounding=ROUND_HALF_EVEN))
                for i in range(2049)]


def packed(values):
    return sum((value & 0xffffffff)<<(32*lane) for lane,value in enumerate(values))


def reference(scores, lut):
    maximum=max(scores)
    exponents=[]
    for score in scores:
        offset=score-maximum+1048576
        if offset<=0: exponents.append(0)
        elif offset>=1048576: exponents.append(65536)
        else:
            point,fraction=divmod(offset,512)
            lo,hi=lut[point:point+2]
            exponents.append(lo+rne((hi-lo)*fraction,512))
    factor=rne(1<<48,sum(exponents))
    return exponents,[rne(exp*factor,1<<32) for exp in exponents]


def make_vectors(path, seed):
    rng=random.Random(seed)
    min_s32=-(1<<31)
    max_s32=(1<<31)-1
    lut=coefficients()
    entries=[(0,1023,[min_s32]),(0,400,[max_s32,min_s32]),(0,305,[7,7,7]),
             (0,3,[-1,-1048577,-1048576,-1048575,0]),(0,11,[-1024,-1025,-1026,0,-1,-2,-3]),
             (0,16,[max_s32]*129),(0,0,[min_s32]*4096)]
    for n in (8,9,63,64,65,127,128,511,512,513,2048):
        center=rng.randrange(min_s32+1048576,max_s32-1048576)
        scores=[center-rng.randrange(-512,1049089) for _ in range(n)]
        scores[0]=center
        if n>9:scores[-1]=center+1024
        entries.append((0,rng.randrange(0,1025-(n+3)//4),scores))
    scores=[rng.randrange(-900000,200000) for _ in range(129)]
    entries.extend(((2,16,scores),(3,16,scores),(4,16,scores),(5,16,scores),(0,16,scores)))
    lines=[]
    for index,(action,base,values) in enumerate(entries):
        n=len(values)
        count=(n+3)//4
        lines.append(f'{action} {seed*100+index} {base} {n} 1 {count}')
        exponent,probability=reference(values,lut)
        for i in range(0,n,4):
            # High lanes may contain valid-sized scores but are out of range.
            source=values[i:i+4]+[max_s32]*max(0,4-(n-i))
            lines.append(' '.join(f'{packed(lanes):032x}' for lanes in (source,exponent[i:i+4],probability[i:i+4])))
    for index,(base,n,commit) in enumerate(((0,0,1),(1023,5,1),(0,4097,1),(10,1,0))):
        lines.append(f'1 {seed*100+90+index} {base} {n} {commit} 0')
    path.write_text('\n'.join(lines)+'\n',encoding='ascii',newline='\n')
    return len(entries)+4


def main(args):
    cores=int(os.environ['OMP_NUM_THREADS'])
    assert os.environ.get('SLURM_JOB_ID') and cores in (10,12) and len(os.sched_getaffinity(0))==cores
    args.out.mkdir(parents=True,exist_ok=False)
    exp=args.source/'project/experiments'
    rtl=args.source/'project/rtl'
    upstream=args.source.parent/'upstream'
    vectors=args.out/'softmax.txt'
    cases=make_vectors(vectors,args.seed)
    report=dict(passed=False,job=os.environ['SLURM_JOB_ID'],seed=args.seed,cases=cases,real_S=True,
                affinity=sorted(os.sched_getaffinity(0)),vectors_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest())
    try:
        build=args.out/'obj-softmax'
        command=['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator',
                 '--binary','--timing','--assert','--Wall','--x-initial','unique','--x-assign','unique',
                 '-Wno-BLKSEQ','--top-module','tb_n32_softmax','--Mdir',str(build),'-j',str(cores),
                 '--timescale-override','1ns/1ps','-I'+str(rtl/'native_s32_n'),
                 str(exp/'native_s32_n/tb_n32_softmax.sv'),str(rtl/'native_s32_n/n_s32_softmax_s128.sv'),
                 str(rtl/'block_v2/block_v2_n_group.sv'),str(exp/'native_s32_dot/s128_lint.vlt'),
                 str(upstream/'local_s_base.sv'),str(upstream/'block_feed_s16k_sram.sv'),
                 str(upstream/'s_sram_256x128_freepdk45.v')]
        with (args.out/'build.log').open('w') as log:
            subprocess.run(command,check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        for init in range(3):
            for mode in (0,1):
                with (args.out/f'softmax-{mode}-{init}.log').open('w') as log:
                    subprocess.run([str(build/'Vtb_n32_softmax'),f'+vectors={vectors}',f'+mode={mode}',
                        f'+verilator+seed+{args.seed}',f'+verilator+rand+reset+{init}'],
                        check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        report['passed']=True
    finally:
        (args.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--seed',type=int,required=True)
    main(parser.parse_args())
