"""Arithmetic envelope and real public-weight record audit (no timing claims)."""
import hashlib
import json
from pathlib import Path
import struct

PUBLIC=Path('/public/home/yuzelu/project-circuit/issue248-public-w8-20261110-01/official-model/model.safetensors')


def audit():
    # Signed A16 x signed W8, 128 terms; FP16 positive finite coefficient.
    partial=128*(1<<15)*128
    gate_bound=128*partial*2047*(1<<(17+5+24))
    down_bound=128*partial*2047*(1<<(48+5-16+40))
    assert partial<(1<<39) and gate_bound<(1<<95) and down_bound<(1<<127)
    result=dict(passed=True,bounds=dict(M_group_abs=partial,gate_upper_bits=gate_bound.bit_length()+1,
        down_upper_bits=down_bound.bit_length()+1,assumptions='K<=16384; S32/Q16 gate/up; S64/Q32 Mid; A16 groups128; positive finite FP16 scales; signed W8',
        final_S32_overflow_policy='fault, never silent clamp; actual model range separately checked'),records=[])
    with PUBLIC.open('rb') as f:
        length=struct.unpack('<Q',f.read(8))[0];header=json.loads(f.read(length));base=8+length
        def read(name,index,count,code):
            item=header[name];width=struct.calcsize(code)
            assert index>=0 and (index+count)*width<=item['data_offsets'][1]-item['data_offsets'][0]
            f.seek(base+item['data_offsets'][0]+index*width)
            return struct.unpack('<'+code*count,f.read(count*width))
        for layer in (0,2,17,35):
            for role in ('gate','up','down'):
                name=f'model.layers.{layer}.mlp.{role}_proj';_,N=header[name+'.qweight']['shape']
                K=header[name+'.qweight']['shape'][0]*4
                for kk in (0,K-128):
                    q=[]
                    zeros=read(name+'.qzeros',(kk//128)*(N//4),2,'i')
                    z=[((zeros[n//4]>>(8*(n%4)))&255)+1 for n in range(8)]
                    rows=[read(name+'.qweight',k*N,8,'i') for k in range(kk//4,(kk+128)//4)]
                    for n in range(8):q.append([((rows[k//4][n]>>(8*(k%4)))&255)-z[n] for k in range(128)])
                    assert all(-128<=v<=127 for row in q for v in row)
                    raw=bytes(v&255 for k in range(0,128,16) for n in range(8) for v in q[n][k:k+16])
                    scales=read(name+'.scales',(kk//128)*N,8,'H')
                    assert all(0<s<0x7c00 for s in scales)
                    record=raw+struct.pack('<8H',*scales)+bytes(48);assert len(record)==1088
                    # Independent consumer walks eight consecutive 128B M beats.
                    for b in range(8):
                        decoded=struct.unpack('<128b',record[b*128:(b+1)*128])
                        assert all(decoded[n*16+j]==q[n][b*16+j] for n in range(8) for j in range(16))
                    result['records'].append(dict(layer=layer,role=role,K_offset=kk,bytes=len(record),
                        sha256=hashlib.sha256(record).hexdigest(),scale_bits=list(scales)))
    result['record_checks']=len(result['records']);return result
