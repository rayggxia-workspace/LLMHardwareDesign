"""Independent full H1024/I3072 integer profile and canonical weight recipe.

The period-251 reduction is exact integer algebra, not tile omission in RTL.
The provider still sends every one of 36,864 chunks and 9,437,184 bytes.
"""
import hashlib
import importlib.util
from pathlib import Path

H=1024
I=3072
PERIOD=251
TOTAL_REQUESTS=36864
WEIGHT_BYTES=9437184
REFERENCE_DEPENDENCIES=['work/Melodydt/151/f16_integer_reference.py']


def prior(root):
    path=Path(root)/REFERENCE_DEPENDENCIES[0]
    spec=importlib.util.spec_from_file_location('f1024_frozen_f16_math',str(path))
    module=importlib.util.module_from_spec(spec)
    exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
    return module


def weight(matrix,n,k,seed):
    return ((13*n+7*k+seed+41*matrix)%251)-125


def request_fields(seq):
    assert 0<=seq<TOTAL_REQUESTS
    if seq<24576:
        return (seq%64)//32,seq//64,seq%32
    return 2,(seq-24576)//96,(seq-24576)%96


def weight_beat(matrix,group,chunk,index,seed):
    tile,part=divmod(index,4)
    return bytes(weight(matrix,group*8+2*part+i//8,chunk*32+tile*8+i%8,seed)&255 for i in range(16))


def canonical_weight_stream(seed,output=None):
    digest=hashlib.sha256();count=0
    stream=open(str(output),'wb') if output else None
    try:
        for seq in range(TOTAL_REQUESTS):
            matrix,group,chunk=request_fields(seq)
            for index in range(16):
                payload=weight_beat(matrix,group,chunk,index,seed)
                digest.update(payload);count+=len(payload)
                if stream:stream.write(payload)
    finally:
        if stream:stream.close()
    assert count==WEIGHT_BYTES
    return {'bytes':count,'sha256':digest.hexdigest(),'requests':TOTAL_REQUESTS,'beats':TOTAL_REQUESTS*16}


def project(x,nout,matrix,seed,f):
    grouped=[0]*PERIOD
    for k,value in enumerate(x):grouped[k%PERIOD]+=value
    raw_period=[sum(value*weight(matrix,n,k,seed) for k,value in enumerate(grouped)) for n in range(PERIOD)]
    raw=[raw_period[n%PERIOD] for n in range(nout)]
    values=[f.clip(f.rne(value,7)) for value in raw]
    return {'raw':raw,'output':[v for v,s in values],'saturated':any(s for v,s in values)}


def f1024(root,x,gamma,seed):
    assert len(x)==len(gamma)==H and all(-32768<=v<=32767 for v in x+gamma)
    f=prior(root);sumsq=sum(v*v for v in x);rad=(sumsq<<16)//H+(1<<16)
    rt=f.floor_sqrt(rad);factor=(1<<38)//rt
    pairs=[f.clip(f.rne(xx*gg*factor,30)) for xx,gg in zip(x,gamma)]
    norm=[v for v,s in pairs]
    gate=project(norm,I,0,seed,f);up=project(norm,I,1,seed,f)
    mid=[];gsat=False
    for start in range(0,I,8):
        result=f.g_vector(0,True,gate['output'][start:start+8],up['output'][start:start+8],8)
        mid.extend(result['output']);gsat|=result['saturated']
    down=project(mid,H,2,seed,f)
    added=[f.clip(a+b) for a,b in zip(down['output'],x)];final=[v for v,s in added]
    words=lambda a:['%032x'%f.pack(a[i:i+8],16) for i in range(0,len(a),8)]
    stages={'X':words(x),'gamma':words(gamma),'norm':words(norm),'gate':words(gate['output']),
            'up':words(up['output']),'mid':words(mid),'down':words(down['output']),'output':words(final)}
    sats={'N_RMS':any(s for v,s in pairs),'M_gate':gate['saturated'],'M_up':up['saturated'],
          'G_mid':gsat,'M_down':down['saturated'],'E_residual':any(s for v,s in added)}
    return {'norm_radicand':rad,'norm_root':rt,'norm_factor':factor,'norm':norm,
            'gate_raw':gate['raw'],'up_raw':up['raw'],'mid':mid,'down_raw':down['raw'],
            'final':final,'words':stages,'ingress_words':stages['X']+stages['gamma'],
            'stage_saturated':sats,'done_saturated':any(sats.values())}
