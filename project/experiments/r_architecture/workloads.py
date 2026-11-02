"""Independent integer oracle and frozen synthetic binary workload corpus."""
from pathlib import Path
import argparse, random, struct, json, hashlib

def rne(x,s):
    q,r=divmod(x,1<<s)
    return q+(r>(1<<(s-1)) or (r==(1<<(s-1)) and q&1))

def transition(state,k,q,x,inject,skip,factors,mode,decay,beta,taps):
    good=True
    def checked(v):
        nonlocal good
        good &= -(1<<31)<=v<(1<<31)
        return (v+(1<<31))%(1<<32)-(1<<31)
    if mode==2:
        out=[checked(rne(x[l]*taps[l]+sum(state[j*8+l]*taps[(j+1)*8+l]for j in range(3)),14))for l in range(8)]
        return good,x+state[:16],out
    n=len(state)//8
    b=[checked(rne(v*(factors[i]if mode else decay),31))for i,v in enumerate(state)]
    err=[]
    if mode==0:
        for l in range(8):
            pred=checked(rne(sum(b[r*8+l]*k[r]for r in range(n)),14))
            err.append(checked(rne(checked(x[l]-pred)*beta,31)))
    b=[checked(v+rne((inject[i%8]if mode else err[i%8])*k[i//8],14))for i,v in enumerate(b)]
    out=[]
    for l in range(8):
        value=checked(rne(sum(b[r*8+l]*q[r]for r in range(n)),14))
        if mode:value=checked(value+rne(x[l]*skip[l],16))
        out.append(value)
    return good,b,out

def create(path,mode,n,layers,tokens,seed,flags=0):
    rng=random.Random(seed);decay=0x70000000;beta=0x50000000
    states=[[rng.randrange(-30000,30001)for _ in range(n)]for _ in range(layers)]
    if flags&1:states=[[0x7fffffff]*n for _ in range(layers)];decay=beta=0x80000000
    with path.open('wb')as f:
        def put(code,values):f.write(struct.pack('<'+str(len(values))+code,*values))
        put('I',[mode,n,layers,tokens,seed,flags,decay,beta])
        for s in states:put('i',s)
        for t in range(tokens):
            for layer in range(layers):
                rows=n//8;k=[rng.randrange(-1024,1025)for _ in range(rows)];q=[rng.randrange(-1024,1025)for _ in range(rows)]
                x=[rng.randrange(-20000,20001)for _ in range(8)];inj=[rng.randrange(-10000,10001)for _ in range(8)];skip=[rng.randrange(-65536,65537)for _ in range(8)]
                factors=[rng.randrange(0,0x80000001)for _ in range(n)]if mode==1 else []
                taps=[rng.randrange(-16384,16385)for _ in range(32)]if mode==2 else []
                if flags&1:k=[32767]*rows;q=k[:];x=[-0x80000000]*8
                if flags&32:states[layer]=[0]*n;k=[0]*rows;q=k[:];x=inj=skip=[0]*8
                put('h',k);put('h',q);put('i',x+inj+skip);put('I',factors);put('h',taps)
                good,candidate,out=transition(states[layer],k,q,x,inj,skip,factors,mode,decay,beta,taps)
                # flags: overflow, rejected commit, reset, response stalls, invalid command, zero.
                committed=good and not(flags&(2|4|16))
                if committed:states[layer]=candidate
                put('I',[int(good),int(committed)]);put('i',out);put('i',states[layer])
    return dict(path=path.name,mode=mode,elements=n,layers=layers,tokens=tokens,seed=seed,flags=flags,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,provenance='synthetic; not real model weights')

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);cases=[]
    for mode in (0,1):
        for n in (256,1024,2048):
            for tokens in (1,16,128):cases.append((f'W0-m{mode}-n{n}-t{tokens}',mode,n,1,tokens,0))
        for layers in (8,24):
            for tokens in (1,16,128):cases.append((f'W1-m{mode}-l{layers}-t{tokens}',mode,1024,layers,tokens,0))
        for n in (4096,8192):
            for tokens in (1,16,128):cases.append((f'W2-m{mode}-n{n}-t{tokens}',mode,n,1,tokens,0))
    for tokens in (1,16,128):cases.append((f'W3-t{tokens}',2,24,1,tokens,0))
    for mode in (0,1,2):
        for flag in (1,2,4,8,16,32):cases.append((f'edge-m{mode}-f{flag}',mode,24 if mode==2 else 256,1,3,flag))
    rows=[create(a.out/(name+'.bin'),mode,n,layers,tokens,157000+i,flags)for i,(name,mode,n,layers,tokens,flags)in enumerate(cases)]
    (a.out/'MANIFEST.json').write_text(json.dumps(dict(format='little-endian schema in workloads.py; full expected state after every token/layer',cases=rows),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),bytes=sum(x['bytes']for x in rows))))
if __name__=='__main__':main()
