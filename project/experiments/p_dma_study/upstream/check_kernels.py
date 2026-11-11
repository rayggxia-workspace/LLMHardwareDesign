"""Independent unbounded-integer oracle; this is not RTL/full-LLM validation."""
import hashlib,json,random,subprocess
from pathlib import Path

def rne_sat(value,shift):
    q,r=divmod(value,1<<shift)
    if 2*r>(1<<shift) or (2*r==(1<<shift) and q%2):q+=1
    return max(-(1<<31),min((1<<31)-1,q))

def main():
    rng=random.Random(240)
    edge=[-(1<<31),(1<<31)-1,-65537,-65536,-32769,-32768,-1,0,1,32767,32768,65535,65536]
    cases=[]
    for a in edge:
        for b in edge:cases.append(([(a,b)],rng.choice([0,1,8,16,31,48,63])))
    for k in [1,2,3,7,8,17,32,127,256,512,2048,11008]:
        for shift in [0,16,31,63]:
            cases.append(([(rng.randrange(-(1<<31),1<<31),rng.randrange(-(1<<31),1<<31)) for _ in range(k)],shift))
    # Positive and negative nearest-even ties with even/odd quotients.
    cases += [([(x,1)],1) for x in [-7,-5,-3,-1,1,3,5,7]]
    text=str(len(cases))+'\n'+''.join(str(len(v))+' '+str(s)+'\n'+''.join(f'{a} {b}\n' for a,b in v) for v,s in cases)
    executable=Path('kernel_probe.exe' if Path('kernel_probe.exe').exists() else 'kernel_probe').resolve()
    p=subprocess.run([str(executable)],input=text,text=True,capture_output=True,check=True)
    actual=list(map(int,p.stdout.split()))
    expected=[rne_sat(sum(a*b for a,b in v),s) for v,s in cases]
    assert actual==expected
    report={'scope':'S32 component reconstruction, full-K 96-bit accumulator bounds and final RNE/saturate; no complete graph/weights/RTL qualification',
            'cases':len(cases),'products':sum(len(v) for v,_ in cases),'seed':240,
            'input_sha256':hashlib.sha256(text.encode()).hexdigest(),'output_sha256':hashlib.sha256(p.stdout.encode()).hexdigest()}
    Path('generated/kernels.json').write_text(json.dumps(report,indent=2)+'\n')
    print('KERNELS_PASS',json.dumps(report))

if __name__=='__main__':main()
