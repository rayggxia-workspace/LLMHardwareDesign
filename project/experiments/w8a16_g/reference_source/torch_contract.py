"""Same exact arithmetic as numpy_contract; parallel tensor operations."""
import torch


def rne(a, s):
    q = torch.bitwise_right_shift(a,s)
    r = a-torch.bitwise_left_shift(q,s)
    half = torch.bitwise_left_shift(torch.ones_like(s),(s-1).clamp_min(0))
    return q+((s>0)&((r>half)|((r==half)&((q&1)!=0)))).long()


def narrow_linear(x, packed, bias, stats, name, width):
    assert bias is None
    raw = getattr(x,'_closure_raw',None)
    frac = getattr(x,'_closure_frac',16)
    if raw is None:
        raw = torch.round(x.double()*(1<<16)).long()
    shape = raw.shape
    a = raw.reshape(-1,shape[-1])
    w,m,e = (torch.from_numpy(t) for t in packed)
    acc = torch.zeros((len(a),w.shape[0]),dtype=torch.int64)
    target_frac = width-16
    row = stats.setdefault(name,dict(values=0,max_abs=0.,nonzero_to_zero=0,max_prefix_abs=0,state_bits=width))
    row['values'] += raw.numel()
    row['max_abs'] = max(row['max_abs'],float(x.abs().max()))
    for k in range(0,a.shape[1],128):
        tile = a[:,k:k+128]
        maximum = tile.abs().amax(1)
        shift = torch.ceil(torch.log2(maximum.double().clamp_min(1)/32767)).clamp_min(0).long()
        q = rne(tile,shift[:,None])
        assert int(q.min()) >= -32768 and int(q.max()) <= 32767
        row['nonzero_to_zero'] += int(((tile!=0)&(q==0)).sum())
        # All integer products/reduction prefixes fit 31 bits. FP64 GEMM is
        # exact here; it is not used for coefficient rounding or accumulation.
        pd = q.double() @ w[:,k:k+128].double().T
        assert torch.equal(pd,torch.round(pd))
        partial = pd.long()
        assert int(partial.min()) >= -(1<<31) and int(partial.max()) < (1<<31)
        assert int(partial.abs().max())*int(m[:,k//128].max()) < (1<<63)
        product = partial*m[None,:,k//128]
        s = shift[:,None]+e[None,:,k//128]+target_frac-frac
        left = s.clamp_min(0)
        assert int(product.abs().max()) << int(left.max()) < (1<<63)
        term = torch.where(s>=0,torch.bitwise_left_shift(product,left),rne(product,(-s).clamp_min(0)))
        assert int(term.abs().max())+int(acc.abs().max()) < (1<<63)
        acc += term
        row['max_prefix_abs'] = max(row['max_prefix_abs'],int(acc.abs().max()))
        assert int(acc.min()) >= -(1<<(width-1)) and int(acc.max()) < (1<<(width-1)), 'Prefix overflow at '+name
    out = rne(acc,torch.tensor(target_frac-16))
    assert int(out.min()) >= -(1<<31) and int(out.max()) < (1<<31)
    raw = out.reshape(*shape[:-1],w.shape[0])
    result = raw.double().div(1<<16).float()
    result._closure_raw = raw
    result._closure_frac = 16
    return result
