"""Independent unbounded integer oracle, RNE contract and RTL test vectors."""
import json
import random
from pathlib import Path


def rne(value, shift, bits):
    if shift < 0 or shift > 63 or bits not in (8,16,32):
        raise ValueError('invalid numeric contract')
    sign = -1 if value < 0 else 1
    magnitude = abs(value)
    q, rem = divmod(magnitude, 1 << shift)
    if shift and (2 * rem > 1 << shift or (2 * rem == 1 << shift and q % 2)):
        q += 1
    return max(-(1 << (bits-1)), min((1 << (bits-1))-1, sign*q))


def pack(values, bits):
    return format(sum((v & ((1 << bits)-1)) << (bits*i) for i,v in enumerate(values)), 'x')


def vectors(out, abits):
    rng=random.Random(248+abits);out=Path(out)
    rows=[];frames=0
    for case,k_total in enumerate([1,7,15,16,17,32,255,256,257,2048,11008,16384]):
        for n in (1,5,8):
            ctx=case%8;acc=[0]*8
            for start in range(0,k_total,16):
                k=min(16,k_total-start)
                a=[rng.randrange(-(1<<(abits-1)),1<<(abits-1)) for _ in range(16)]
                b=[[rng.randrange(-128,128) for _ in range(16)] for _ in range(8)]
                # include exact signed extrema, not merely small random values
                if case%2==0:a[0]=-(1<<(abits-1));b[0][0]=-128
                for j in range(n):acc[j]+=sum(a[t]*b[j][t] for t in range(k))
                last=start+k==k_total;frames+=int(last)
                aw=32 if abits==8 else 40
                assert all(-(1<<(aw-1))<=v<1<<(aw-1) for v in acc)
                rows.append(f'{ctx} {int(start==0)} {int(last)} {k} {n} {start} '+pack(a,abits)+' '+pack(sum(b,[]),8)+' '+pack(acc,aw))
    out.write_text('\n'.join(rows)+'\n',encoding='utf8')
    return dict(packets=len(rows),frames=frames,ABITS=abits,accumulator_bits=32 if abits==8 else 40)


def check_contract():
    checks=0
    for bits in (8,16):
        for s in (0,1,3,15,31):
            for x in [-2147483648,-32769,-32768,-129,-128,-7,-5,-3,-1,0,1,3,5,7,127,128,32767,32768,2147483647]:
                # independently use Python's exact rational ties-even rounding
                from fractions import Fraction
                expected=max(-(1<<(bits-1)),min((1<<(bits-1))-1,round(Fraction(x,1<<s))))
                assert rne(x,s,bits)==expected;checks+=1
    return dict(passed=True,checks=checks,quality_verified=False,
                contract='W8; symmetric signed A8/A16; per-input-tile power-of-two activation scale; common full-K scale; final per-output-channel scale and RNE; scales cannot change silently across K')


if __name__=='__main__':
    print(json.dumps(check_contract()))
