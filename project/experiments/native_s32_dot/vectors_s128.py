"""Finite-window service vectors. Generation executes only on Slurm."""
import hashlib
import json
import random
from oracle import S32_MIN,S32_MAX,dot,pack


def generate(out,seed,witness,capacity):
    rng=random.Random(seed);lines=[];tag=0;cases=0;key=seed<<64
    def emit(kind,key=key,full=0,offset=0,chunk=0,n=0,rows=1,shift=0,layout=0,
             abase=0,bbase=128,resultbase=900,committed=1,error=0,aborted=0,done=0,abort_mode=0,result=None):
        nonlocal tag
        result=[0]*(capacity*8) if result is None else result+[0]*(capacity*8-len(result))
        fields=(kind,key,tag,full,offset,chunk,n,rows,shift,layout,abase,bbase,resultbase,committed,error,aborted,done,abort_mode,pack(result,32))
        lines.append(' '.join(format(v,'x') for v in fields));tag+=1
    def word(address,values):emit(3,abase=address,result=values)
    def stage(a,b,offset,length,layout):
        n=len(b[0])
        for row,data in enumerate(a):
            for kk in range(0,128,4):word(row*32+kk//4,[data[offset+kk+j] if kk+j<length else 0 for j in range(4)])
        if layout==0:
            for c in range(n):
                for kk in range(0,128,4):word(128+c*32+kk//4,[b[offset+kk+j][c] if kk+j<length else 0 for j in range(4)])
        else:
            for kk in range(128):
                data=b[offset+kk] if kk<length else [0]*n
                for group in range(2):word(128+kk*2+group,(data+[0]*(8-n))[group*4:group*4+4])
    samples=[]
    edges=(S32_MIN,S32_MAX,-1,0,1,-32769,32768)
    for layout in (0,1):
        for k in (1,3,4,5,16,127,128,129,512):
            for n in (1,3,4,5,8):
                rows=1+(len(samples)%capacity)
                a=[[rng.choice(edges) for _ in range(k)] for _ in range(rows)]
                b=[[rng.choice(edges) for _ in range(n)] for _ in range(k)]
                samples.append(dict(a=a,b=b,layout=layout,shift=rng.randrange(64),role='boundary'))
    for item in json.loads(witness.read_text()):
        samples.append(dict(a=[item['A']],b=item['B'],layout=0 if item['role']=='QK' else 1,
                            shift=item.get('shift',item.get('node',{}).get('attributes',{}).get('shift',0)),role='real-witness'))
    for sample in samples:
        key+=1;a,b=sample['a'],sample['b'];k=len(a[0]);n=len(b[0]);rows=len(a);layout=sample['layout'];shift=sample['shift']
        result=[]
        for values in a:result+=dot(values,b,shift)+[0]*(8-n)
        emit(0,key=key,full=k,n=n,rows=rows,shift=shift,layout=layout)
        # A new owner cannot be silently created; invalid descriptors cannot
        # issue an S request or release the current owner.
        emit(0,key=key+1,full=k,n=n,rows=rows,error=1)
        emit(1,key=key,offset=0,chunk=min(128,k),committed=0,error=1)
        emit(1,key=key,offset=1,chunk=min(128,k),error=1)
        for offset in range(0,k,128):
            length=min(128,k-offset);stage(a,b,offset,length,layout)
            final=offset+length==k
            emit(1,key=key,offset=offset,chunk=length,rows=rows,done=int(final),result=result if final else None)
        cases+=1
    # Live abort while reads are outstanding, while a write offer is held,
    # and an actual returned read-error. Partial final writes are reported,
    # never called rollback. The bench derives the ACK mask independently.
    for layout in (0,1):
        for abort_mode in (1,2,3):
            key+=1;k=128;n=8;a=[[rng.choice(edges) for _ in range(k)] for _ in range(capacity)]
            b=[[rng.choice(edges) for _ in range(n)] for _ in range(k)];result=[]
            for values in a:result+=dot(values,b,24)
            emit(0,key=key,full=k,n=n,rows=capacity,shift=24,layout=layout)
            stage(a,b,0,k,layout)
            emit(1,key=key,chunk=k,rows=capacity,done=1,error=1,aborted=1,abort_mode=abort_mode,result=result)
            cases+=1
    key+=1;emit(0,key=key,full=128,n=8,rows=capacity)
    emit(2,key=key+1,error=1);emit(2,key=key,done=1,aborted=1)
    emit(1,key=key,chunk=128,error=1);emit(3,abase=1023,result=[0x12345678]*4)
    emit(0,key=key+1,full=0,n=1,error=1)
    path=out/'service.txt';path.write_text('\n'.join(lines)+'\n')
    return dict(cases=cases,seed=seed,rows_capacity=capacity,multiplier_lanes=capacity*4,
                vectors_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                witness_sha256=hashlib.sha256(witness.read_bytes()).hexdigest(),
                scope='Single logical S128 RTL service with bounded RTT2+stall provider; upstream staged writes are explicit fixture actions, not DDR qualification.')
