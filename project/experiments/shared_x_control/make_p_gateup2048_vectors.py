"""Compute-node-only synthetic Gate/Up, ordinary W8, two RF owners over K2048."""
import argparse,hashlib,json,struct,zlib
from pathlib import Path
from fractions import Fraction
from make_p_executor_vectors import mem,fp
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
K=2048;tilecount=K//128
A=[((i*13+i//128*7)%7)-3 for i in range(K)]
inputs=[struct.pack('<8h',*A[i:i+8]) for i in range(0,K,8)]
d=bytearray(128);struct.pack_into('<IHHII',d,0,0x02505001,128,2,0x02504d02,25001)
struct.pack_into('<IIII',d,16,1,9,8,7);struct.pack_into('<IIII',d,32,1000,2000,1,100)
struct.pack_into('<QQIIHBBHHHBBHHHHH',d,48,0x100000,0x200000,8,0,8,1,0,K,0,K,2,0,0,128,160,200,240)
struct.pack_into('<I',d,124,zlib.crc32(d[:124]));payloads=[];outputs=[];prefixes=[]
for way in range(2):
    state=[0]*8;prefix=[]
    for kk in range(tilecount):
        payload=bytearray(1088);dot=[0]*8
        for tile in range(8):
            for n in range(8):
                for k in range(16):
                    w=((kk*3+tile*7+n*11+k*5+way*(2+n%3))%5)-2
                    struct.pack_into('<b',payload,tile*128+n*16+k,w)
                    dot[n]+=A[kk*128+tile*16+k]*256*w
        scales=[0x1800 if (n+way)%2 else 0x1c00 for n in range(8)]
        struct.pack_into('<8H',payload,1024,*scales)
        state=[v+round(Fraction(x)*fp(s)) for v,x,s in zip(state,dot,scales)]
        assert all(-(1<<31)<=v<(1<<31) for v in state)
        payloads.append(bytes(payload));prefix.append(list(state))
    prefixes.append(prefix);outputs.extend((struct.pack('<4i',*state[:4]),struct.pack('<4i',*state[4:])))
mem(a.out/'scopes.mem',[bytes(d)],128);mem(a.out/'A.mem',inputs,16)
b=b''.join(payloads);mem(a.out/'DDR.mem',[b[i:i+64] for i in range(0,len(b),64)],64)
mem(a.out/'expected.mem',outputs,16)
manifest={'schema':'synthetic-GateUp-K2048/1','K':K,'tiles':tilecount,'N_each_way':8,'rf_contexts':2,'scope_service':2,'A16_after_real_quant':'Aold*256; dynamically calculated shift0','weights':'synthetic signedW8[-2,2], distinct gate/up deployments','scales_fp16':[0x1800,0x1c00],'RNE':'perK128 Fraction ties-even then checkedS32 prefix','prefixes':prefixes,'final':[p[-1] for p in prefixes],'CRC32':f'{zlib.crc32(d[:124]):08x}','DDRbytes':len(b),'DDRSHA256':hashlib.sha256(b).hexdigest(),'claim':'synthetic W8A16 Gate/Up projection only; no G/Down, checkpoint quality or whole FFN throughput'}
(a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
