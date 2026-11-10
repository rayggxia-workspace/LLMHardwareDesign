"""Identical X, distinct Gate/Up output stripes; exact integer reference."""
import argparse,hashlib,json,struct,zlib
from pathlib import Path
from fractions import Fraction
from make_p_executor_vectors import mem,fp

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--groups',type=int,choices=(1,8),default=1)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
K=2048;tiles=K//128;groups=a.groups
A=[((i*13+i//128*7)%7)-3 for i in range(K)]
inputs=[struct.pack('<8h',*A[i:i+8]) for i in range(0,K,8)]
payloads=[];outputs=[];prefixes=[];descriptors={1:[],2:[]}
for stripe in range(2):
    for mode in (1,2):
        d=bytearray(128)
        struct.pack_into('<IHHII',d,0,0x02505001,128,mode,0x02504d02,25001)
        struct.pack_into('<IIII',d,16,1,9,8,7)
        struct.pack_into('<IIII',d,32,1000+16*stripe,2000+16*stripe,1,100+512*stripe)
        struct.pack_into('<QQIIHBBHHHBBHHHHH',d,48,0x100000+0x200000*stripe,0x200000+0x200000*stripe,8*groups,0,8,groups,0,K,0,K,2,0,
                         256 if mode==1 else 0,128+64*stripe,160+64*stripe,640,672)
        struct.pack_into('<I',d,124,zlib.crc32(d[:124]));descriptors[mode].append(bytes(d))
    for way in range(2):
        for group in range(groups):
            state=[0]*8;prefix=[]
            for kk in range(tiles):
                payload=bytearray(1088);dot=[0]*8
                for tile in range(8):
                    for n in range(8):
                        for k in range(16):
                            w=((kk*3+tile*7+n*11+k*5+way*(2+n%3)+stripe*(2+tile%2)+group*(1+(k+n)%3))%5)-2
                            struct.pack_into('<b',payload,tile*128+n*16+k,w)
                            dot[n]+=A[kk*128+tile*16+k]*256*w
                scales=[0x1800 if (n+way+stripe+group)%2 else 0x1c00 for n in range(8)]
                struct.pack_into('<8H',payload,1024,*scales)
                state=[v+round(Fraction(x)*fp(s)) for v,x,s in zip(state,dot,scales)]
                assert all(-(1<<31)<=v<(1<<31) for v in state)
                payloads.append(bytes(payload));prefix.append(list(state))
            prefixes.append(prefix)
            outputs.extend((struct.pack('<4i',*state[:4]),struct.pack('<4i',*state[4:])))
mem(a.out/'resident-scopes.mem',descriptors[1],128);mem(a.out/'scopes.mem',descriptors[2],128)
mem(a.out/'A.mem',inputs,16)
b=b''.join(payloads);mem(a.out/'DDR.mem',[b[i:i+64] for i in range(0,len(b),64)],64);mem(a.out/'expected.mem',outputs,16)
manifest={'schema':'resident-X-two-stripe/2','K':K,'tiles':tiles,'N_each_way':8*groups,'rf_contexts':2*groups,
          'resident_S_words':[256,511],'S_bytes_per_P':16384,'resident_payload_bytes_within_existing_S':4096,
          'A16_after_real_quant':'Aold*256; dynamically calculated shift0','weights':'synthetic signedW8[-2,2], four distinct gate/up arrays',
          'RNE':'perK128 Fraction ties-even then checkedS32 prefix','prefixes':prefixes,'final':[p[-1] for p in prefixes],
          'DDRbytes':len(b),'DDRSHA256':hashlib.sha256(b).hexdigest(),
          'claim':'one P, each mode pays actual initial writes/quant/header/COPY, synthetic numerics, no full FFN or system performance'}
(a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

