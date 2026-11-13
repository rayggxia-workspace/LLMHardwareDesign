"""Compute-node synthetic long streamed projection oracle, no model-quality claim."""
import argparse,hashlib,json,struct,zlib
from pathlib import Path
from fractions import Fraction
from make_p_executor_vectors import mem,fp
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
K=11008;tilecount=K//128
A=[((i*13+i//128*7)%5)-2 for i in range(K)]
inputs=[struct.pack('<8h',*A[i:i+8]) for i in range(0,K,8)]
d=bytearray(128);struct.pack_into('<IHHII',d,0,0x02505001,128,2,0x02504d02,25001)
struct.pack_into('<IIII',d,16,1,9,8,7);struct.pack_into('<IIII',d,32,1000,2000,1,100)
struct.pack_into('<QQIIHBBHHHBBHHHHH',d,48,0x100000,0,8,0,8,1,0,K,0,K,1,0,0,128,160,200,240)
struct.pack_into('<I',d,124,zlib.crc32(d[:124]));payloads=[];prefix=[];state=[0]*8
for kk in range(tilecount):
    payload=bytearray(1088);dot=[0]*8
    for tile in range(8):
        for n in range(8):
            for k in range(16):
                w=((kk*3+tile*7+n*11+k*5)%3)-1
                struct.pack_into('<b',payload,tile*128+n*16+k,w)
                dot[n]+=A[kk*128+tile*16+k]*256*w
    struct.pack_into('<8H',payload,1024,*([0x1c00]*8))
    state=[v+round(Fraction(x)*fp(0x1c00)) for v,x in zip(state,dot)]
    assert all(-(1<<31)<=v<(1<<31) for v in state)
    payloads.append(bytes(payload));prefix.append(list(state))
mem(a.out/'scopes.mem',[bytes(d)],128);mem(a.out/'A.mem',inputs,16)
b=b''.join(payloads);mem(a.out/'DDR.mem',[b[i:i+64] for i in range(0,len(b),64)],64)
mem(a.out/'expected.mem',[struct.pack('<4i',*state[:4]),struct.pack('<4i',*state[4:])],16)
manifest={'schema':'synthetic-long-stream/1','K':K,'tiles':tilecount,'N':8,'scope_service':2,'A16_after_real_quant':'Aold*256; dynamically calculated shift0','weights':'synthetic signedW8[-1,0,1]','scales_fp16':0x1c00,'RNE':'perK128 Fraction ties-even then checkedS32 prefix','prefixes':prefix,'final':state,'CRC32':f'{zlib.crc32(d[:124]):08x}','DDRbytes':len(b),'DDRSHA256':hashlib.sha256(b).hexdigest(),'claim':'synthetic long-range function only; not checkpoint quality or whole FFN or performance'}
(a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
