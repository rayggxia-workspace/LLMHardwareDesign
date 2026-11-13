"""Compute-node E32 exact integer oracle and strict RTL regression."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess


def pack(lanes, width):
    return sum((value % (1 << width)) << (width * i) for i, value in enumerate(lanes))


def oracle(op, shift, mask, minus, a, b, c):
    if (op not in range(12) or not -63 <= shift <= 63 or
            (op not in (2, 3, 4) and shift) or (op not in (0, 1) and minus) or
            (op == 0 and minus & 4)):
        return 0, 0, 1
    values = []
    clips = 0
    bits = 16 if op in (4, 7, 8) else 32
    for i, (x, y, z) in enumerate(zip(a, b, c)):
        if not mask & (1 << i):
            values.append(-(1 << 31) if op == 11 else 0)
            continue
        if op in (0, 1):
            raw = sum((-1 if minus >> j & 1 else 1) * v for j, v in enumerate((x, y, z)[:op+2]))
        elif op == 2:
            raw = x * y
        elif op in (3, 4, 10, 11):
            raw = x
        elif op in (5, 6):
            raw = (min if op == 5 else max)(x, y)
        elif op in (7, 8):
            raw = int(x < y if op == 7 else x <= y)
        else:
            raw = y if x else z
        if shift < 0:
            raw *= 1 << -shift
        elif shift:
            divisor = 1 << shift
            q, r = divmod(raw, divisor)
            raw = q + int(2*r > divisor or (2*r == divisor and q % 2 != 0))
        output = max(-(1 << (bits-1)), min((1 << (bits-1))-1, raw))
        clips |= int(output != raw) << i
        values.append(output)
    return pack(values, bits), clips, 0


def vectors(seed, path):
    rng = random.Random(seed)
    edges = [-(1 << 31), (1 << 31)-1, -65536, -32769, -3, -1, 0, 1, 3, 32768, 65535]
    def lane():
        return rng.choice(edges) if rng.randrange(3) else rng.randrange(-(1 << 31), 1 << 31)
    rows = []
    for i in range(768):
        op = i % 12
        mask = rng.randrange(16)
        minus = rng.randrange(1 << (2 if op == 0 else 3)) if op in (0, 1) else 0
        shift = ((i//12)*19 + 7*(i%12)) % 127 - 63 if op in (2, 3, 4) else 0
        a,b,c = [[lane() for _ in range(4)] for _ in range(3)]
        if op == 9:
            a = [0, 1, -1, 0]
        if i % 41 == 0:
            op = 12 + i % 4
        elif i % 43 == 0:
            shift = 64
        elif i % 47 == 0:
            op,shift,minus,mask = 3,1,0,15
            a = [-5,-3,-1,3]
        elif i % 53 == 0:
            op,shift,minus,mask = 2,-63,0,15
            a,b = [-1,1,0,-(1 << 31)], [1,1,1,-(1 << 31)]
        data, clip, error = oracle(op, shift, mask, minus, a, b, c)
        frame = pack(a,32) | (pack(b,32)<<128) | (pack(c,32)<<256) | (data<<384)
        frame |= op<<512 | (shift%256)<<516 | mask<<524 | minus<<528 | clip<<531 | error<<535
        rows.append(f'{frame:0134x}')
    path.write_text('\n'.join(rows)+'\n', encoding='ascii')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--verilator', required=True)
    a=p.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('only allocated compute job')
    a.out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ);env.pop('VERILATOR_ROOT',None)
    path=a.out/'vectors.hex';vectors(a.seed,path)
    args=[a.verilator,'--binary','--timing','--assert','-Wall','--top-module','test_e_s32_native',
          '--x-initial','unique','--x-assign','unique','-j','10','--Mdir',str(a.out/'obj'),
          str(a.source/'project/rtl/w8a16_v1/e_s32_native.sv'),
          str(a.source/'project/experiments/block_local_native/test_e_s32_native.sv')]
    with (a.out/'build.log').open('w') as log:
        subprocess.run(args,env=env,cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True)
    results=[]
    for init in range(3):
        target=a.out/f'initial-{init}.log'
        with target.open('w') as log:
            subprocess.run([str(a.out/'obj/Vtest_e_s32_native'),f'+vectors={path}',f'+seed={a.seed}',
                 f'+verilator+rand+reset+{init}',f'+verilator+seed+{a.seed}'],env=env,cwd=a.out,
                 stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
        passes=[s for s in target.read_text().splitlines() if s.startswith('PASS e_s32_native commands=768 returned=768 ')]
        assert len(passes)==1
        results.append(dict(initial=init,receipt=passes[0]))
    result=dict(seed=a.seed,results=results,hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
         for p in a.out.iterdir() if p.is_file()},qualification='E32 pointwise core functional only, no finite S/LC/STA')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
