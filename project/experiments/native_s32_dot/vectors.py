import hashlib
import json
from pathlib import Path
import random
from oracle import S32_MIN,S32_MAX,dot,pack


def generate(out,seed,witness):
    rng=random.Random(seed);lines=[];tag=0;owner=seed<<64;cases=0
    def emit(kind,key=0,full=0,k=0,group=0,n=0,shift=0,a=0,b=None,error=0,done=0,result=None):
        nonlocal tag
        b=[0]*4 if b is None else b
        result=[0]*8 if result is None else result+[0]*(8-len(result))
        values=[kind,key,tag,full,k,group,n,shift,a&0xffffffff,pack(b,32),error,done,pack(result,32)]
        lines.append(' '.join(format(x,'x') for x in values));tag+=1
    # Cancel waits for already accepted STEP responses; reset flushes an
    # independently observed live pipeline. Numeric cases follow fresh BEGIN.
    emit(0,key=owner,full=32,n=8)
    emit(1,key=owner,k=0,group=0,a=S32_MIN,b=[S32_MAX]*4)
    emit(1,key=owner,k=0,group=1,a=S32_MIN,b=[S32_MAX]*4)
    emit(2,key=owner,done=1)
    emit(0,key=owner,full=32,n=8)
    emit(1,key=owner,k=0,group=0,a=17,b=[19]*4)
    emit(4) # bench action: asynchronous task reset, not a hardware opcode
    samples=[]
    for index,k in enumerate((1,2,3,16,127,128,129,512,65535)):
        n=1 if k==65535 else (index%8)+1
        edges=[S32_MIN,S32_MAX,-1,0,1,32768,-32769]
        a=[rng.choice(edges) for _ in range(k)]
        b=[[rng.choice(edges) for _ in range(n)] for _ in range(k)]
        samples.append(dict(A=a,B=b,shift=(0,1,16,24,31,47,63,1,63)[index],role='boundary'))
    samples+=json.loads(witness.read_text())
    # Explicit positive/negative halfway and just-outside-saturation cases.
    for a,b,s in [([3],[[1]],1),([-3],[[1]],1),([1],[[1]],1),([-1],[[1]],1),
                  ([S32_MIN],[[S32_MIN]],0),([S32_MAX],[[S32_MAX]],63)]:
        samples.append(dict(A=a,B=b,shift=s,role='ties/overflow'))
    for index,sample in enumerate(samples):
        a,b=sample['A'],sample['B'];n=len(b[0]);k=len(a)
        shift=sample.get('shift',sample.get('node',{}).get('attributes',{}).get('shift',0))
        key=owner+index+1;expected=dot(a,b,shift);emit(0,key=key,full=k,n=n,shift=shift)
        emit(0,key=key,full=k,n=n,shift=shift,error=1)
        for kk,x in enumerate(a):
            for group in range((n+3)//4):
                data=b[kk][group*4:group*4+4];data+=[0]*(4-len(data))
                if kk==0 and group==0:
                    emit(1,key=key+100000,k=kk,group=group,a=x,b=data,error=1)
                    emit(1,key=key,k=kk+1,group=group,a=x,b=data,error=1)
                    if n<4:emit(1,key=key,k=kk,group=group,a=x,b=[1]*4,error=1)
                if group==1 and kk==0:
                    emit(1,key=key,k=kk,group=group,a=x^1,b=data,error=1)
                final=kk==k-1 and group==(n-1)//4
                emit(1,key=key,k=kk,group=group,a=x,b=data,done=int(final),result=expected if final else None)
        cases+=1
    emit(0,full=0,n=1,error=1);emit(0,full=1,n=0,error=1);emit(0,full=1,n=9,error=1)
    emit(1,error=1);emit(2,error=1);emit(3,error=1)
    path=out/'core.txt';path.write_text('\n'.join(lines)+'\n')
    return dict(cases=cases,commands=len(lines)-1,reset_actions=1,seed=seed,
                vectors_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                witness_sha256=hashlib.sha256(witness.read_bytes()).hexdigest(),
                coverage='Exact full-K dot/RNE/saturation, real PR220 QK/AV slice, signed extrema, pipeline backpressure/reset/cancel; no S frontend or physical proof')
