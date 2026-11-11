"""Generate independent integer vectors and shape-bound staged NExp inputs."""
import hashlib,json,random,re,sys
from collections import Counter
from decimal import Decimal,localcontext,ROUND_HALF_EVEN
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'s16_vector_native'))
from vectors import oracle,signed,rne

CASES=['unary_s16','binary_s16','ternary_s16','narrow_s32','mixed_edges','hazards','direct','backpressure','io_contention']
def word(vals):return sum((v&65535)<<(16*i) for i,v in enumerate(vals))
def lanes(w):return [signed(w>>(16*i),16) for i in range(8)]
def trace(path):
    it=iter(Path(path).read_text().split());nt,no,tokens=(int(next(it)) for _ in range(3));ts=[];ops=[]
    for _ in range(nt):ts.append(tuple(int(next(it)) for _ in range(4)))
    for i in range(no):
        out=int(next(it));kind=next(it);q=[int(next(it)) for _ in range(8)];ins=[int(next(it)) for _ in range(q[-1])]
        ops.append(dict(index=i,out=out,kind=kind,elements=q[0],rows=q[1],cols=q[2],k=q[3],batches=q[4],shift=q[5],layout=q[6],inputs=ins,
                        input_bits=[ts[t][2] for t in ins],output_bits=ts[out][2]))
    assert next(it,None) is None
    return ts,ops,tokens

def prepare(root,out):
    root,out=Path(root),Path(out);repo=root/'source';out.mkdir(exist_ok=False)
    rng=random.Random(2474401);edges=[-32768,32767,-1,0,1,-128,127,256,1024,-1024,16384,-16384,3,-3,5,-5]
    cases=[]
    for name in CASES:
        mem=[word([edges[(a+j)%len(edges)] if a%2==0 else rng.randrange(-32768,32768) for j in range(8)]) for a in range(1024)]
        start=mem.copy();rows=[];traffic=Counter();coverage=Counter();n=128 if name in ['mixed_edges','hazards','direct'] else 64
        for i in range(n):
            op,shift,src,store,direct,abort,dst=0,0,[i%128,128+i%128],1,0,0,512+i%128
            if name=='unary_s16':op=11;src=src[:1]
            elif name=='ternary_s16':op=3;shift=13;src.append(256+i%128)
            elif name=='narrow_s32':op=13;shift=8;src=src[:1]
            elif name=='mixed_edges':
                op=i%16;shift=(i//16)*4;arity=3 if op in [3,6] else 1 if op in [7,8] or op>=10 else 2
                sources=[0,1,2,3][i//16%4];src=[i%128,128+i%128,256+i%128][:sources];store=i%5!=0
            elif name=='hazards':
                op=[0,1,2,3][i%4];shift=7 if op in [2,3] else 0
                src=[512+(i-1)%8,512+(i-2)%8];dst=512+i%8
                if op==3:src.append(512+(i-3)%8)
                if i%5==0:dst=src[0]
            elif name=='direct':
                op=i%14;shift=i%16;arity=3 if op in [3,6] else 1 if op in [7,8] or op>=10 else 2
                src=[i%128,128+i%128,256+i%128][:arity];direct=1;abort=i%11==0
            source_count=len(src);dv=word([edges[(i+j+2)%len(edges)] for j in range(8)])
            operands=[0,0,0]
            for j,a in enumerate(src):operands[j]=dv if j==0 and direct else mem[a]
            if abort:result,error,sat=0,1,0
            else:result,error,sat=oracle(op,shift,*(lanes(x) for x in operands))
            if store and not error:mem[dst]=result;traffic['writes']+=1
            traffic['reads']+=0 if abort else source_count-int(bool(direct))
            coverage[str(op)]+=1
            packed=(op<<308)|(shift<<303)|(source_count<<301)|(int(store)<<300)|(direct<<299)|(int(abort)<<298)|\
                (sum(a<<(10*j) for j,a in enumerate(src))<<268)|(dst<<258)|(dv<<130)|(error<<129)|(sat<<128)|result
            rows.append(f'{packed:078x}')
        for filename,contents in [('initial.hex',[f'{x:032x}' for x in start]),('final.hex',[f'{x:032x}' for x in mem]),('commands.hex',rows)]:
            (out/(name+'-'+filename)).write_text('\n'.join(contents)+'\n')
        cases.append(dict(name=name,count=n,stress=int(name in ['backpressure','direct','hazards']),contention=int(name=='io_contention'),traffic=dict(traffic),op_counts=dict(coverage)))
    # Independent high-precision generation of the documented LUT, checked
    # against every immutable RTL table sample; interpolation follows its ABI.
    with localcontext() as ctx:
        ctx.prec=60;lut=[int(((Decimal(-16)+Decimal(i)/64).exp()*32768).to_integral_value(rounding=ROUND_HALF_EVEN)) for i in range(1025)]
    text=(repo/'project/rtl/block_v2/block_v2_n_exp.svh').read_text()
    actual={int(i):int(v) for i,v in re.findall(r"11'd(\d+):exp_lut=16'd(\d+)",text)}
    assert len(actual)==1025 and all(actual[i]==x for i,x in enumerate(lut))
    values=[]
    for i in range(22016):
        x=edges[i%len(edges)] if i%5==0 else -(i*47%16385)
        if x< -16384:y=0
        elif x>=0:y=32768
        else:
            index,frac=divmod(x+16384,16);y=lut[index]+rne((lut[index+1]-lut[index])*frac,4)
        values.append(f'{((x&65535)<<32)|y:012x}')
    (out/'nexp-values.hex').write_text('\n'.join(values)+'\n')
    audits={};regions=[]
    for name in ['decode512','decode2048','prefill2']:
        path=root/'inputs'/(name+'.trace');ts,ops,tokens=trace(path)
        nexp=[o for o in ops if o['kind']=='NExp'];eligible=[o for o in ops if o['kind'] in ['Add','Sub','Product','Maximum','Minimum','RoPE'] and
            o['input_bits'] and all(b==16 for b in o['input_bits']) and o['output_bits']==16 and len(o['inputs'])<=3 and 0<=o['shift']<=31]
        audits[name]=dict(trace_sha256=sha(path),tokens=tokens,NExp=nexp,eligible_pure_S16_E=len(eligible),
            S32_to_S16_converts=sum(o['kind']=='Convert' and o['input_bits']==[32] and o['output_bits']==16 for o in ops),
            shift_outside_5bit=sum(not 0<=o['shift']<=31 for o in ops),
            values_scope='shape/width only; no activation values or complete quantization scales in trace')
        if name=='prefill2':
            assert len(nexp)==36 and all(o['elements']==22016 and o['input_bits']==[16] and o['output_bits']==32 and o['shift']==0 for o in nexp)
            for o in nexp:
                regions.append(dict(operation=o['index'],input_tensor=o['inputs'][0],output_tensor=o['out'],elements=o['elements'],
                    staged_tiles=344,values_per_tile=64,NX16_descriptors=2752,source_layout='packed S16',destination_layout='packed S32',
                    required_scale='signed Q5.10 (not proven by trace)',numeric_input='constructed nexp-values.hex'))
    result=dict(cases=cases,trace_audit=audits,regions=regions,numeric_scope='actual trace shapes; constructed Q5.10, no real weights/activations',
        LUT_samples_independently_verified=1025,seed=2474401,generated_sha256={p.name:sha(p) for p in out.iterdir() if p.is_file()})
    (out/'generation.json').write_text(json.dumps(result,indent=2)+'\n');return result
