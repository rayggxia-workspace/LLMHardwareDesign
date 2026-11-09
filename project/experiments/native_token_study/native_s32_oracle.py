"""Independent exact-integer proof for paid S32 -> native-S16 lowering.

No model/RTL implementation imports, simulator, weights or server calls.
These checks establish arithmetic and finite layout contracts, not LLM quality.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random

RADIX=1<<15
SHIFTS=(0,15,30)


def require(ok,message):
    if not ok:raise ValueError(message)


def signed(value,bits):
    require(-(1<<(bits-1))<=value<(1<<(bits-1)),f'signed{bits} overflow')
    return value


def limbs(value):
    """Balanced signed15 digits; top digit fits [-2,2], including S32_MAX."""
    signed(value,32);q=value;result=[]
    for _ in range(2):
        digit=(q+RADIX//2)%RADIX-RADIX//2
        result.append(signed(digit,15));q=(q-digit)//RADIX
    require(-2<=q<=2,'S32 top digit');result.append(q)
    require(sum(d*(1<<s) for d,s in zip(result,SHIFTS))==value,'limb reconstruction')
    return tuple(result)


def round32(value,shift):
    require(0<=shift<=63,'final RNE shift outside agreed contract')
    unit=1<<shift;quotient,remainder=divmod(value,unit)
    if remainder*2>unit or (remainder*2==unit and quotient%2):quotient+=1
    return max(-(1<<31),min((1<<31)-1,quotient))


def native_scale(partial,factor,shift):
    signed(partial,40);signed(factor,16);require(0<=shift<=31,'native scale shift exceeds31')
    product=signed(partial*factor,56)
    return signed(product*(1<<shift),64)


def schedule(k):
    require(k>0 and 3*k<=65535,'flattened three-limb K overflows native context')
    result=[];next_k=0
    for start in range(0,k,32):
        length=min(32,k-start);tiles=(length+7)//8;last_k=length-8*(tiles-1)
        for limb in range(3):
            offset=3*start+limb*length
            require(offset==next_k,'non-contiguous flattened native K')
            first=start==0 and limb==0;final=start+length==k and limb==2
            result.append(dict(source_row=limb,shift=15*limb,offset=offset,k=length,tiles=tiles,
                               last_k=last_k,first=first,final=final))
            next_k+=length
    require(next_k==3*k and sum(r['first'] for r in result)==1 and sum(r['final'] for r in result)==1,
            'first/final or terminal K mismatch')
    return result


def native16_digits(value,wide):
    if not wide:return ((signed(value,8),0),)
    signed(value,16)
    return ((value%128,0),((value//128)%128,7),(value//16384,14))


def native_chunk(a,b,bits_b,inner_check=False):
    require(1<=len(a)<=32 and len(a)==len(b),'invalid native chunk')
    for x in a:signed(x,16)
    for y in b:signed(y,bits_b)
    direct=signed(sum(x*y for x,y in zip(a,b)),40)
    if inner_check:
        accum=0
        # Mirrors the *contracted arithmetic order*, independently of the RTL
        # implementation: tile, A digit, B digit. Every prefix must fit S40.
        for start in range(0,len(a),8):
            for ai in range(3):
                for bi in range(3 if bits_b==16 else 1):
                    delta=0;shift=0
                    for x,y in zip(a[start:start+8],b[start:start+8]):
                        ax,ash=native16_digits(x,True)[ai];by,bsh=native16_digits(y,bits_b==16)[bi]
                        delta+=ax*by;shift=ash+bsh
                    accum=signed(accum+(delta<<shift),40)
        require(accum==direct,'native S8-digit arithmetic differs from S16 dot')
    return direct


def old_static(a,b,bits_b):
    """Old legal op10 rows3, full-K raw S64, then paid external96 merge."""
    rows=[0,0,0]
    for start in range(0,len(a),32):
        chunk=a[start:start+32];weights=b[start:start+32]
        split=[limbs(x) for x in chunk]
        for limb in range(3):
            partial=native_chunk([v[limb] for v in split],weights,bits_b)
            rows[limb]=signed(rows[limb]+native_scale(partial,1,0),64)
    merged=0
    for limb in range(3):merged=signed(merged+(rows[limb]<<SHIFTS[limb]),96)
    return merged


def new_static(a,b,bits_b):
    """New op13 single mathematical context, op4 scale changes, flat3K."""
    program=schedule(len(a));accum=0
    for command in program:
        # Recover original source K independently from command lengths/order.
        if command['source_row']==0:source_start=command['offset']//3
        length=command['k'];limb=command['source_row']
        partial=native_chunk([limbs(x)[limb] for x in a[source_start:source_start+length]],
                             b[source_start:source_start+length],bits_b)
        accum=signed(accum+native_scale(partial,1,command['shift']),64)
    return accum


def dynamic_terms(a,b):
    """Each chunk/pair is a completed native term; 96bit math context is external."""
    total=0;terms=0;next_k=0
    for start in range(0,len(a),32):
        length=min(32,len(a)-start);require(start==next_k,'external merge K order')
        aa=[limbs(x) for x in a[start:start+length]];bb=[limbs(y) for y in b[start:start+length]]
        for ai in range(3):
            for bi in range(3):
                raw=signed(native_chunk([x[ai] for x in aa],[y[bi] for y in bb],16),64)
                total=signed(total+(raw<<(15*(ai+bi))),96);terms+=1
        next_k+=length
    require(next_k==len(a) and terms==9*((len(a)+31)//32),'dynamic native term count')
    return total


def pair_rmw(scratch,pair,delta):
    """Two16B-word RMW of a packed pair24B; preserve adjacent eight bytes."""
    require(len(scratch)==96 and 0<=pair<4 and len(delta)==2,'S96 pair layout')
    offset=pair*24;first=offset//16;window=bytearray(scratch[first*16:first*16+32]);local=offset-first*16
    for lane in range(2):
        at=local+12*lane
        value=int.from_bytes(window[at:at+12],'little',signed=True)
        window[at:at+12]=signed(value+delta[lane],96).to_bytes(12,'little',signed=True)
    scratch[first*16:first*16+32]=window
    return first,first+1


def expected_group_work(k,n,bits_b,group_size=1):
    """Lower bounds/contracts only: sourceDDR residency is intentionally separate."""
    require(1<=n<=8 and bits_b in (8,16,32) and 1<=group_size<=8,'work shape')
    tiles=(k+7)//8;chunks=(k+31)//32
    result=dict(k=k,n=n,group_size=group_size,raw_A_logical_bytes=4*k,
                raw_B_logical_bytes=k*n*(bits_b//8),packed_A_S_write_bytes=64*tiles,
                A_feeder_wire_bytes=48*tiles,A_wide_reads=tiles,
                packed_B_S_write_bytes=(3*128 if bits_b==32 else 64*(bits_b//8))*tiles,
                packed_A_chunk_peak=64*((min(k,32)+7)//8),
                packed_B_chunk_peak=(3*128 if bits_b==32 else 64*(bits_b//8))*((min(k,32)+7)//8))
    if bits_b!=32:
        result.update(old_native_op10=chunks,new_native_op13=3*chunks,new_scale_op4=3*chunks,
                      old_raw_op3=12,old_merge_terms=3,new_raw_op3=0,new_merge_terms=0,
                      old_S96_clear_narrow_writes=6,old_S96_RMW_narrow_reads=24,old_S96_RMW_narrow_writes=24,
                      old_pair_merge_cycles_if_3cycles=36,new_release_op14=1,
                      new_live_native_contexts=group_size,flat_next_k=3*k)
    else:
        terms=9*chunks
        # The first tested fallback uses nine legacy row1 jobs and separate
        # padded single-row A planes, not free source-row selection in old M.
        result.update(packed_A_S_write_bytes=192*tiles,A_feeder_wire_bytes=144*tiles,
                      A_wide_reads=9*tiles,packed_A_chunk_peak=192*((min(k,32)+7)//8))
        result.update(native_terms=terms,raw_op3=4*terms,release_op14=terms,
                      S96_bytes_per_math_context=96,S96_clear_narrow_writes=6,
                      S96_RMW_narrow_reads=8*terms,S96_RMW_narrow_writes=8*terms,
                      external_S96_bytes_peak=96*group_size,native_temporary_contexts=1,
                      pair_merge_cycles_if_3cycles=12*terms)
        result['release_op14']=0 # legacy op10 temporary rows, not live op13 slots
    return result


def trace_format_gate(path):
    """Independent format rejection; eligibility alone is not native qualification."""
    fields=iter(path.read_text(encoding='utf-8').split())
    nt,no,tokens=(int(next(fields)) for _ in range(3));require(nt>0 and no>=0 and tokens>0,'trace header')
    tensors=[];histogram={}
    for wanted in range(nt):
        tensor_id,elements,bits,initial=(int(next(fields)) for _ in range(4))
        require(tensor_id==wanted and elements>=0,'trace tensor order')
        tensors.append(dict(id=tensor_id,elements=elements,bits=bits,initial=bool(initial)))
        histogram[bits]=histogram.get(bits,0)+1
    matrix_ops=0
    for _ in range(no):
        output=int(next(fields));kind=next(fields)
        elements,rows,cols,k,batches,shift,layout,count=(int(next(fields)) for _ in range(8))
        inputs=[int(next(fields)) for _ in range(count)]
        require(0<=output<nt and all(0<=i<output for i in inputs),'trace topology')
        if kind=='Dot':matrix_ops+=1
    require(next(fields,None) is None,'unexpected trace suffix')
    unsupported=[t for t in tensors if t['bits'] not in (8,16)]
    return dict(trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),tensor_count=nt,op_count=no,tokens=tokens,
                matrix_op_count=matrix_ops,bitwidth_histogram=histogram,
                native_format_gate_passed=not unsupported,unsupported_tensor_count=len(unsupported),unsupported_examples=unsupported[:8],
                native_complete_graph_qualified=False,
                scope='format rejection only; does not prove native U, command lowering, DMA or quality')


def run():
    rng=random.Random(247320);cases=0;products=0;input_digest=hashlib.sha256();output_digest=hashlib.sha256()
    edges=[-(1<<31),-(1<<31)+1,-65537,-32769,-16385,-16384,-1,0,1,16383,16384,32767,65535,(1<<31)-1]
    for value in edges+[rng.randrange(-(1<<31),1<<31) for _ in range(2000)]:limbs(value)
    require(limbs((1<<31)-1)==(-1,0,2) and limbs(-(1<<31))==(0,0,-2),'S32 extrema')
    static_bound=65535*((1<<31)+(1<<29)+(1<<14))*(1<<15)
    require(static_bound<1<<63,'static all-prefix absolute S64 bound')
    require(32*49151*49151<1<<39,'native S16 digit-prefix S40 bound')
    for bits in (8,16,32):
        for k in (1,3,7,8,9,31,32,33,63,64,65,256,2048,11008):
            a=[rng.choice(edges) if i%5==0 else rng.randrange(-(1<<31),1<<31) for i in range(k)]
            b=[rng.randrange(-(1<<(bits-1)),1<<(bits-1)) for _ in range(k)]
            a[0]=-(1<<31);b[0]=-(1<<(bits-1))
            direct=sum(x*y for x,y in zip(a,b));signed(direct,96)
            if bits==32:
                candidate=dynamic_terms(a,b);require(candidate==direct,'dynamic reconstruction')
            else:
                baseline=old_static(a,b,bits);candidate=new_static(a,b,bits)
                require(baseline==direct==candidate,'old/new static full precision mismatch')
            for shift in (0,15,31,63):
                answer=round32(candidate,shift);require(answer==round32(direct,shift),'premature RNE/clamp')
                output_digest.update((str(answer)+'\n').encode());cases+=1
            input_digest.update(json.dumps([bits,a,b],separators=(',',':')).encode());products+=k
    for bits in (8,16):
        for k in (1,7,8,9,31,32):
            a=[rng.choice((-32768,-16384,-1,0,1,16383,32767)) for _ in range(k)]
            b=[rng.randrange(-(1<<(bits-1)),1<<(bits-1)) for _ in range(k)]
            native_chunk(a,b,bits,True)
    for k in (1,7,8,9,31,32,33,21845):schedule(k)
    rejected=[]
    for name,call in (
        ('flat3K_overflow',lambda:schedule(21846)),
        ('scale_shift32',lambda:native_scale(1,1,32)),
        ('factor_positive32768',lambda:native_scale(1,32768,0)),
        ('scaled_S64_overflow',lambda:native_scale((1<<39)-1,32767,31)),
        ('dynamic_S64_counterexample',lambda:signed(2*((-(1<<31))**2),64)),
        ('S96_overflow',lambda:signed(1<<95,96)),
    ):
        try:call()
        except ValueError:rejected.append(name)
        else:raise AssertionError('negative contract accepted '+name)
    # Actual packed-word sharing: pair0/pair1 shareword1, pair2/pair3 shareword4.
    values=[(i+1)*(1<<70)-i for i in range(8)]
    scratch=bytearray().join(v.to_bytes(12,'little',signed=True) for v in values)
    touched=[]
    for pair in range(4):
        before=[int.from_bytes(scratch[12*i:12*i+12],'little',signed=True) for i in range(8)]
        delta=(13+pair,-29-pair);touched.append(pair_rmw(scratch,pair,delta))
        after=[int.from_bytes(scratch[12*i:12*i+12],'little',signed=True) for i in range(8)]
        require(after==[v+(delta[i-2*pair] if 2*pair<=i<2*pair+2 else 0) for i,v in enumerate(before)],'packed96 neighbor corrupted')
    require(touched==[(0,1),(1,2),(3,4),(4,5)],'RMW word budget')
    return dict(passed=True,scope='independent exact S32 lowering, native scale/offset bounds, packed96 RMW; no RTL/whole-model/quality qualification',
                seed=247320,cases=cases,source_products=products,input_sha256=input_digest.hexdigest(),output_sha256=output_digest.hexdigest(),
                negative_contracts_rejected=rejected,packed96_pair_words=touched,
                native_static_max_k=65535//3,external96_hardware_implemented=False,
                static_S64_absolute_prefix_bound_at_K65535=static_bound,
                examples=[expected_group_work(11008,8,b,8) for b in (8,16,32)])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path)
    parser.add_argument('--trace',type=Path);parser.add_argument('--require-native',action='store_true')
    args=parser.parse_args()
    admission=trace_format_gate(args.trace) if args.trace else None
    if args.require_native and (admission is None or not admission['native_format_gate_passed']):
        print(json.dumps(dict(passed=False,error='require-native rejects absent/unsupported original trace formats',admission=admission),indent=2))
        raise SystemExit(2)
    report=run()
    if admission:report['admission']=admission
    text=json.dumps(report,indent=2)+'\n'
    if args.out:args.out.write_text(text,encoding='utf-8')
    print(text,end='')
