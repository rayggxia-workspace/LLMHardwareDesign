"""Exact payload arithmetic with explicit host-generated scale descriptors.

No whole-LLM or production-hardware claim: this is a W8/A16 FFN candidate.
G is the unchanged two-lane Q5.10 leaf. Wide Mid multiplication and spilled
contexts are separate candidate services, never silently attributed to G/M.
"""
from fractions import Fraction
import math
import random


def rne(value, shift):
    q,r=divmod(int(value),1<<int(shift))
    return q+int(shift>0 and (r*2>1<<shift or r*2==1<<shift and q%2))


def clamp(value,bits):return max(-(1<<(bits-1)),min((1<<(bits-1))-1,int(value)))


def coefficient(ratio):
    if not math.isfinite(ratio) or ratio<=0:raise ValueError('invalid scale ratio')
    candidates=[]
    for shift in range(64):
        mult=round(math.ldexp(ratio,shift))
        if 1<=mult<=32767:candidates.append((abs(math.ldexp(mult,-shift)-ratio),mult,shift))
    if not candidates:raise ValueError('scale ratio not representable by positive S16 multiplier/right-shift')
    error,m,s=min(candidates)
    return m,s,error/ratio


def activation(raw):
    raw=int(raw)
    if raw< -8192:return 0
    if raw>8192:return raw
    index,frac=divmod(raw+8192,32)
    def silu(x):return x/(1+math.exp(-x))
    x=-8+index/32
    lo=round(silu(x)*1024);hi=round(silu(x if index==512 else x+1/32)*1024)
    return lo+rne((hi-lo)*frac,5)


def native_g(x,up=None):
    value=activation(x)
    if up is not None:value=rne(value*int(up),10)
    return clamp(value,16),not -32768<=value<=32767


def tests():
    rng=random.Random(24817);checks=0
    for shift in (0,1,5,10,31,47,63):
        for value in [-(1<<63),-32769,-7,-5,-3,-1,0,1,3,5,7,32768]+[rng.randrange(-(1<<62),1<<62) for _ in range(80)]:
            assert rne(value,shift)==round(Fraction(value,1<<shift));checks+=1
    for ratio in (2**-45,.0001,.125,1.,100.,32767.):
        m,s,e=coefficient(ratio);assert 0<m<=32767 and 0<=s<=63 and e<.0001;checks+=1
    assert native_g(4096)[0]==activation(4096)
    assert native_g(4096,20480)[1] # SiLU(4)*20 overflows fixed Q5.10.
    return dict(passed=True,RNE_coefficient_checks=checks)


def convert_array(values,ratios,bits):
    import numpy as np
    values=np.asarray(values,dtype=np.int64);ratios=np.broadcast_to(ratios,values.shape)
    output=np.empty(values.shape,dtype=np.int64);params=[];saturated=0;worst=0.
    for index in range(values.size):
        v=int(values.flat[index]);m,s,e=coefficient(float(ratios.flat[index]))
        exact=rne(v*m,s);out=clamp(exact,bits);output.flat[index]=out
        saturated+=int(exact!=out);worst=max(worst,e);params.append((v,m,s,out,exact!=out))
    return output,dict(saturated=saturated,max_coefficient_relative_error=worst),params


def bounded_down(weights,mid,reference):
    """Sequential finite-resource numerical witness, NOT existing M/LC support.

    Hold one <=128-value Mid tile until all consumers finish. Only 64 outputs
    can be active in each P; every other live partial is explicitly in private
    SRAM. This verifies payload/storage ownership, without claiming overlap.
    """
    import numpy as np
    H,F=weights.shape;P=3;N=8;contexts=8;tile=128
    columns=[np.concatenate([np.arange(c,min(c+N,H)) for c in range(p*N,H,P*N)]) for p in range(P)]
    saved=[np.zeros(len(c),dtype=np.int64) for c in columns]
    result=np.zeros(H,dtype=np.int64);reads=writes=0;peak=0
    for k in range(0,F,tile):
        stop=min(F,k+tile);held=mid[k:stop].copy();consumers=0
        for p,cols in enumerate(columns):
            for start in range(0,len(cols),N*contexts):
                end=min(start+N*contexts,len(cols));active=saved[p][start:end].copy()
                peak=max(peak,len(active));assert len(active)<=64
                if k:reads+=len(active)*5
                active+=weights[cols[start:end],k:stop].astype(np.int64)@held
                assert int(np.abs(active).max())<1<<39
                if stop==F:result[cols[start:end]]=active
                else:saved[p][start:end]=active;writes+=len(active)*5
                consumers+=1
        assert consumers==sum((len(c)+63)//64 for c in columns)
        # Source tile may now be released. No next tile was admitted early.
    assert np.array_equal(result,reference)
    assert reads==writes==((F+tile-1)//tile-1)*H*5
    return dict(bit_exact=True,max_active_outputs_per_P=peak,Mid_buffer_values=tile,
                psum_read_bytes=reads,psum_write_bytes=writes,partial_bits=40,
                requires_new_context_save_reload_service=True,cycle_timing_qualified=False)


def ffn_sample(x,weights,scales,out,tag):
    import numpy as np
    from numeric import pack
    x=np.asarray(x,dtype=np.float64);sx=max(float(np.abs(x).max())/32767,1e-30)
    qa=np.rint(x/sx).clip(-32768,32767).astype(np.int64)
    gate=weights['gate'].astype(np.int64)@qa;up=weights['up'].astype(np.int64)@qa
    assert max(int(np.abs(gate).max()),int(np.abs(up).max()))<1<<39
    gq,gstats,gparams=convert_array(gate,sx*scales['gate']*1024,16)
    uq,ustats,uparams=convert_array(up,sx*scales['up']*1024,16)
    activated=np.array([activation(v) for v in gq],dtype=np.int64)
    gated_pairs=[native_g(g,u) for g,u in zip(gq,uq)]
    mid_gated=np.array([v for v,_ in gated_pairs],dtype=np.int64)
    # Wide candidate retains integer up accumulator; no fused-G output saturation.
    mid_wide=activated*up
    assert int(np.abs(mid_wide).max())<1<<63
    rows=[];conversion_sets=[('gate_to_G',gparams),('up_to_G',uparams)]
    for label,raw,scale in [('native_gated',mid_gated,1/1024),('ungated_G_wide_product',mid_wide,sx*scales['up']/1024)]:
        actual=raw*np.asarray(scale);sm=max(float(np.abs(actual).max())/32767,1e-30)
        qm,stats,params=convert_array(raw,np.asarray(scale)/sm,16)
        conversion_sets.append((label+'_Mid_to_down',params))
        down=weights['down'].astype(np.int64)@qm
        assert int(np.abs(down).max())<1<<39
        reconstructed=down*(sm*scales['down'])
        np.savez(out/(tag+'-'+label+'.npz'),Mid=qm,down_raw=down,down_scales=sm*scales['down'])
        # Exact full-K accumulation after every K tile; partials never rounded.
        w=weights['down'];tiled=np.zeros(w.shape[0],dtype=np.int64)
        for start in range(0,w.shape[1],128):
            tiled+=w[:,start:start+128].astype(np.int64)@qm[start:start+128]
        assert np.array_equal(down,tiled),'tiled accumulation changes payload'
        xf=x;gfloat=weights['gate'].astype(np.float64)@xf*scales['gate'];ufloat=weights['up'].astype(np.float64)@xf*scales['up']
        mf=gfloat/(1+np.exp(-gfloat))*ufloat
        ref=weights['down'].astype(np.float64)@mf*scales['down']
        nmse=float(np.sum((reconstructed-ref)**2)/max(float(np.sum(ref**2)),1e-30))
        rows.append(dict(profile=label,output_relative_L2=math.sqrt(nmse),
            output_cosine=float(np.dot(reconstructed,ref)/max(np.linalg.norm(reconstructed)*np.linalg.norm(ref),1e-30)),
            Mid_convert=stats,down_accum_max_abs=int(np.abs(down).max()),K128_tiling_bit_exact=True,
            bounded_partial_schedule=bounded_down(weights['down'],qm,down),
            hardware_qualified=False,scale_discovery='host float64; integer payload thereafter'))
    # Real integer accumulators and compiled descriptors exercise requant RTL.
    req=[]
    conversion_coverage={}
    for stage,all_params in conversion_sets:
        indices=set(np.linspace(0,len(all_params)-1,1024,dtype=int).tolist())
        indices.update(i for i,v in enumerate(all_params) if v[4])
        indices.add(max(range(len(all_params)),key=lambda i:abs(all_params[i][0])))
        sampled=[all_params[i] for i in sorted(indices)]
        conversion_coverage[stage]=dict(values=len(sampled),saturated=sum(int(v[4]) for v in sampled))
        for start in range(0,len(sampled),4):
            items=sampled[start:start+4];count=len(items)
            req.append(f'{pack([v[0] for v in items],64)} {pack([v[1] for v in items],16)} {pack([v[2] for v in items],6)} {count} '+
                       f'{pack([v[3] for v in items],16)} {sum(int(v[4])<<i for i,v in enumerate(items)):x} 0')
    # Pair samples over all channels, not just a favorable small interval.
    gv=[]
    selected=set(np.linspace(0,len(gq)//2-1,512,dtype=int).tolist())
    selected.update(i//2 for i,v in enumerate(gated_pairs) if v[1])
    selected.update(i//2 for i,v in enumerate(uparams) if v[4])
    selected.update(i//2 for i,v in enumerate(gparams) if v[4])
    for j in sorted(selected):
        a=gq[2*j:2*j+2];b=uq[2*j:2*j+2]
        for gated in (False,True):
            pairs=[native_g(int(v),int(u) if gated else None) for v,u in zip(a,b)]
            gv.append(f'{int(gated)} {pack(a,16)} {pack(b,16)} {pack([v[0] for v in pairs],16)} {int(any(v[1] for v in pairs))}')
    return dict(tag=tag,A_scale=sx,gate_conversion=gstats,up_conversion=ustats,
                G_product_saturated=sum(int(s) for _,s in gated_pairs),G_values=len(gq),
                RTL_conversion_coverage=conversion_coverage,rows=rows),req,gv


if __name__=='__main__':
    import json
    print(json.dumps(tests()))
