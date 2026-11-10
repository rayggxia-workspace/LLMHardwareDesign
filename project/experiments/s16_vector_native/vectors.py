"""Independent integer E oracle: Python integers, explicit RNE and saturation."""
import hashlib,json,random
from pathlib import Path

def signed(n,bits):
    n&=(1<<bits)-1
    return n-(1<<bits) if n>>(bits-1) else n

def rne(n,s):
    if not s:return n
    q,r=divmod(n,1<<s)
    return q+int(r>(1<<(s-1)) or (r==(1<<(s-1)) and q&1))

def oracle(op,shift,a,b,c):
    if op>13:return 0,1,0
    out=0;sat=0
    for i in range(8):
        x,y,z=a[i],b[i],c[i]
        if op==0:v=x+y
        elif op==1:v=x-y
        elif op==2:v=x*y
        elif op==3:v=x*y+z
        elif op==4:v=max(x,y)
        elif op==5:v=min(x,y)
        elif op==6:v=x if z else y
        elif op==7:v=x<<shift
        elif op==8:v=x>>shift
        elif op==9:v=x*b[i&6]+(-1 if i%2==0 else 1)*a[i^1]*b[i|1]
        elif op==11:v=abs(x)
        elif op==13:v=signed((a[2*i]&65535)|((a[2*i+1]&65535)<<16),32) if i<4 else 0
        else:v=x
        if op in (2,3,9,10,13):v=rne(v,shift)
        bits=8 if op==12 else 16
        lo,hi=-(1<<(bits-1)),(1<<(bits-1))-1
        sat|=int(v<lo or v>hi);v=min(hi,max(lo,v))
        out|=(v&((1<<bits)-1))<<(bits*i)
    return out,0,sat

def generate(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rng=random.Random(2473801);edge=[-32768,32767,-1,0,1,-16384,16384,127,-128,255,-255,3,-3,5,-5,1024]
    rows=[];counts={str(op):0 for op in range(16)};saturated=0
    for op in range(16):
        for shift in range(32):
            for sample in range(8):
                banks=[[edge[(i+sample+bank*3+shift)%len(edge)] if sample<4 else rng.randrange(-32768,32768) for i in range(8)] for bank in range(3)]
                expected,error,sat=oracle(op,shift,*banks);counts[str(op)]+=1;saturated+=sat
                words=[sum((v&65535)<<(16*i) for i,v in enumerate(b)) for b in banks]
                packed=(shift<<518)|(op<<514)|(words[0]<<386)|(words[1]<<258)|(words[2]<<130)|(error<<129)|(sat<<128)|expected
                rows.append(f'{packed:0131x}')
    file=out/'e-vectors.hex';file.write_text('\n'.join(rows)+'\n',encoding='ascii')
    receipt=dict(count=len(rows),values=len(rows)*8,per_opcode=counts,saturated=saturated,
        seed=2473801,oracle='Python unbounded integers; floor-divmod RNE; signed16 saturation; explicit S32 narrow',
        sha256=hashlib.sha256(file.read_bytes()).hexdigest())
    (out/'vectors.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    return receipt
