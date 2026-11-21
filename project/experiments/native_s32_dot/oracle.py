"""Independent arbitrary-precision full-K signed32 dot contract. Refs #252."""
S32_MIN=-(1<<31)
S32_MAX=(1<<31)-1


def finish(value,shift):
    assert 0<=shift<=63
    q,r=divmod(value,1<<shift)
    if shift and (r>1<<(shift-1) or (r==1<<(shift-1) and q&1)):
        q+=1
    return min(S32_MAX,max(S32_MIN,q))


def dot(a,b,shift):
    assert a and len(a)==len(b) and 1<=len(a)<=65535
    n=len(b[0]);assert 1<=n<=8
    assert all(S32_MIN<=x<=S32_MAX for x in a)
    assert all(len(row)==n and all(S32_MIN<=x<=S32_MAX for x in row) for row in b)
    return [finish(sum(x*row[c] for x,row in zip(a,b)),shift) for c in range(n)]


def pack(values,bits):
    return sum((value&((1<<bits)-1))<<(i*bits) for i,value in enumerate(values))
