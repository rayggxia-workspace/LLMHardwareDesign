"""Integer contract: power-of-two activation groups, FP16 W8 scales, wide G.

Reference payload operations use exact Python integers. Torch screening uses
decoded integer inputs with FP32 dot products, and is not a bit-exact full LLM.
"""
import math
import numpy as np
from precision_oracle import rne

G_FRAC=16
G_LUT=[round((x/(1+math.exp(-x)))*(1<<16)) for x in (i/64-16 for i in range(2049))]


def silu32(raw):
    raw=int(raw)
    if raw<=-(16<<16):return 0
    if raw>=(16<<16):return raw
    i,f=divmod(raw+(16<<16),1024)
    return G_LUT[i]+rne((G_LUT[i+1]-G_LUT[i])*f,10)


def fp16_fields(scales):
    bits=np.asarray(scales,dtype=np.float16).view(np.uint16)
    e=((bits>>10)&31).astype(np.int16);f=(bits&1023).astype(np.int64)
    assert not (bits>>15).any() and (e!=31).all() and (bits!=0).all()
    return np.where(e==0,f,f+1024),np.where(e==0,-24,e-25).astype(np.int16)


def unpack_gptq(qweight,qzeros,scales,g_idx):
    w=np.asarray(qweight,dtype=np.int32);z=np.asarray(qzeros,dtype=np.int32)
    shifts=np.array([0,8,16,24],dtype=np.int64)
    raw=((w.astype(np.int64)[:,None,:]>>shifts[None,:,None])&255).reshape(-1,w.shape[1]).T
    zeros=(((z.astype(np.int64)[:,:,None]>>shifts[None,None,:])&255).reshape(z.shape[0],-1)+1).T
    idx=np.asarray(g_idx,dtype=np.int64)
    assert np.array_equal(idx,np.arange(len(idx))//128),'activation reorder not supported'
    quant=raw-zeros[:,idx]
    assert quant.min()>=-128 and quant.max()<=127,'public artifact requires a wider signed weight than W8'
    # A second scalar implementation checks packed coordinates independently.
    rng=np.random.default_rng(24821)
    for _ in range(64):
        n=int(rng.integers(raw.shape[0]));k=int(rng.integers(raw.shape[1]))
        a=(int(w[k//4,n])>>(8*(k%4)))&255
        b=((int(z[k//128,n//4])>>(8*(n%4)))&255)+1
        assert int(quant[n,k])==a-b
    scale=np.asarray(scales,dtype=np.float16).T.copy();m,e=fp16_fields(scale)
    return quant.astype(np.int8),scale,m,e


def normalize(raw,bits):
    raw=np.asarray(raw,dtype=np.int64)
    maximum=max(abs(int(v)) for v in raw)
    shift=max(0,maximum.bit_length()-(bits-1))
    limit=(1<<(bits-1))-1
    while maximum>limit*(1<<shift):shift+=1
    q=np.array([rne(v,shift) for v in raw],dtype=np.int64)
    assert q.min()>=-limit-1 and q.max()<=limit
    return q,shift


def dot(raw,frac,weights,mantissas,exponents,bias=None,group=128,bits=16):
    """Exact group accumulation; final RNE only after all weighted partials."""
    raw=np.asarray(raw,dtype=np.int64);H,K=weights.shape
    assert K==len(raw) and K%group==0 and 128%group==0
    E=min(0,int(exponents.min())-(frac-16))
    acc=[0]*H;max_bits=0
    for k in range(0,K,group):
        q,shift=normalize(raw[k:k+group],bits)
        p=weights[:,k:k+group].astype(np.int64)@q
        m=mantissas[:,k//128];e=exponents[:,k//128]
        for n in range(H):
            term=int(p[n])*int(m[n]);s=shift+int(e[n])-(frac-16)-E
            assert s>=0
            acc[n]+=term<<s
            max_bits=max(max_bits,abs(acc[n]).bit_length()+1)
            assert -(1<<127)<=acc[n]<(1<<127),'S128 partial overflow'
    result=np.array([rne(v,-E) for v in acc],dtype=np.int64)
    if bias is not None:result+=np.rint(np.asarray(bias,dtype=np.float64)*(1<<16)).astype(np.int64)
    assert result.min()>=-(1<<31) and result.max()<(1<<31),'S32/Q16 output range'
    return result,dict(max_partial_bits=max_bits,common_exponent=E,group=group,bits=bits)


def ffn(raw,weights,fields):
    gate,gs=dot(raw,16,weights['gate'],*fields['gate'])
    up,us=dot(raw,16,weights['up'],*fields['up'])
    mid=np.array([silu32(g)*int(u) for g,u in zip(gate,up)],dtype=np.int64)
    down,ds=dot(mid,32,weights['down'],*fields['down'])
    # Independent finite SRAM partial schedule reorders outputs and K groups.
    H,F=weights['down'].shape;E=ds['common_exponent'];result=np.zeros(H,dtype=np.int64)
    reads=writes=0;peak=0
    owners=[np.concatenate([np.arange(c,min(c+8,H)) for c in range(p*8,H,24)]) for p in range(3)]
    saved=[[0]*len(cols) for cols in owners]
    for k in range(0,F,128):
        tile=mid[k:k+128].copy();q,shift=normalize(tile,16)
        for p,cols in enumerate(owners):
            for first in range(0,len(cols),64):
                selected=cols[first:first+64];active=saved[p][first:first+len(selected)]
                peak=max(peak,len(active));assert len(active)<=64
                if k:reads+=len(active)*16
                partial=weights['down'][selected,k:k+128].astype(np.int64)@q
                for j,n in enumerate(selected):
                    m=fields['down'][0][n,k//128];e=fields['down'][1][n,k//128]
                    active[j]+=(int(partial[j])*int(m))<<(shift+int(e)-16-E)
                    assert -(1<<127)<=active[j]<(1<<127)
                if k+128==F:
                    for j,n in enumerate(selected):result[n]=rne(active[j],-E)
                else:saved[p][first:first+len(selected)]=active;writes+=len(active)*16
        # Current Mid source lease expires only after every group has committed.
    assert np.array_equal(result,down)
    assert reads==writes==(F//128-1)*H*16
    return down,gate,up,mid,dict(gate=gs,up=us,down=ds,
        bounded_down_bit_exact=True,active_output_peak=peak,Mid_buffer_values=128,
        partial_read_bytes=reads,partial_write_bytes=writes,
        S128_bytes_per_P=[len(c)*16 for c in owners])


def tests():
    rng=np.random.default_rng(248)
    max_error=0.
    for x in np.linspace(-32,32,10001):
        q=round(x*(1<<16));ref=x/(1+math.exp(-x))
        max_error=max(max_error,abs(silu32(q)/(1<<16)-ref))
    assert max_error<.00004
    for bits in (8,16):
        for _ in range(100):normalize(rng.integers(-(1<<50),1<<50,128,dtype=np.int64),bits)
    return dict(passed=True,G_math_max_abs_error=max_error,normalization_cases=200)
