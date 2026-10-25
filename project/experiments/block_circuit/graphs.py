"""Causal graph microcode. Only entry inputs are initialized; all intermediates are RTL."""
import hashlib,json
from pathlib import Path
def add_chains(C,vectors,granite,byte,encode,operand):
 def save(name,kind,w,f,outs,expected,status=0,source=None):
  pc=C.allocate([*w,15]);vectors.append({'name':name,'kind':kind,'pc':pc,'lane':len(vectors)%8,'expected_status':status,'input':f.hex(),'outputs':outs,'expected':expected,'source':source})
 def run(w,op,a,b,dst,n,shift=0,selector=None):
  o=C.invoke(w,op,a,b,shift,selector);w.extend(byte(0,r,dst=dst+i)for i,r in enumerate(o['value']['refs'][:n]));return o
 def output(addr,n,signed=True):return {'signed':signed,'refs':list(range(addr,addr+n))}
 rq=[(1234567,1073741824,31),(-2147483648,1073741824,130),(2147483647,1073741824,131),(17,99,-1)]
 for i,(a,b,s)in enumerate(rq):
  f=bytearray(512);w=[]
  for off,val,n in[(256,a,4),(260,b,4),(272,s,8),(280,0,8),(288,128,8)]:encode(f,off,val,n)
  run(w,'mul_s32_s32',256,260,304,8)
  o=C.invoke(w,'cmp_s64',272,280);w.extend([byte(8,o['less']['refs'][0],-2,dst=344),byte(11,344,check=True)])
  run(w,'sub_s64',288,272,296,8);run(w,'max_s64',296,280,296,8);run(w,'sub_s64',288,296,296,8)
  run(w,'rne_s64_i32',304,None,320,4,selector=296)
  save('rq_chain'+str(i),'rq_chain',w,f,{'value':output(320,4)},{'a':a,'b':b,'raw_shift':s},7 if s<0 else 0)
 merges=[]
 if granite:
  import numpy as np
  for folder in granite:
   folder=Path(folder);manifest=json.loads((folder/'manifest.json').read_text());report=json.loads((folder/'report.json').read_text())
   if manifest['status']!='EXECUTED_COMPLETE'or(report['router_bits'],report['split'],report['tokens'])!=(16,'evaluation',72):raise ValueError('frozen actual R16 evaluation input')
   entry=next(x for x in manifest['artifacts']if x['path']=='runtime.npz');digest=hashlib.sha256((folder/'runtime.npz').read_bytes()).hexdigest()
   if digest!=entry['sha256']:raise ValueError('actual runtime SHA')
   source={'directory':str(folder),'runtime_sha256':digest,'layer':report['layer'],'scope':'actual full8 selected outputs at coordinate0 through original residual join; next1536norm outside this cut'}
   with np.load(folder/'runtime.npz',allow_pickle=False)as z:
    for t in(0,64,71):merges.append(([int(x)for x in z['down_q12'][t,:,0]],[int(x)for x in z['router.gate_q15'][t]],int(z['residual_q12'][t,0]),{'moe':int(z['moe_q12'][t,0]),'scaled':int(z['scaled_moe_q12'][t,0]),'joined':int(z['layer_output_q12'][t,0])},{**source,'token':t}))
 if not merges:merges=[([100,-90,80,-70,60,-50,40,-30],[4096]*8,123,None,{'kind':'synthetic_only'})]
 for i,(down,gates,residual,original,source)in enumerate(merges):
  f=bytearray(512);w=[]
  for k in range(8):encode(f,256+4*k,down[k],4);encode(f,288+2*k,gates[k],2,False)
  encode(f,320,230687,4);encode(f,324,residual,4)
  for k in range(8):run(w,'mul_s32_u16',256+4*k,288+2*k,312,8);run(w,'add_s64',304,312,304,8)
  run(w,'rne_s64_i32',304,None,312,8,15);w.extend(byte(0,312+k,dst=344+k)for k in range(4))
  run(w,'mul_s32_s32',312,320,312,8);run(w,'rne_s64_i32',312,None,312,8,20);w.extend(byte(0,312+k,dst=352+k)for k in range(4))
  run(w,'align_s32_i64',324,None,336,8);run(w,'add_s64',312,336,312,8);run(w,'rne_s64_i32',312,None,328,4)
  save('merge8_chain'+str(i),'merge8_chain',w,f,{'moe':output(344,4),'scaled':output(352,4),'joined':output(328,4)},{'down':down,'gates':gates,'residual':residual,'original':original},source=source)
 for i,xs in enumerate(([4096,-4096,2048,-2048,1024,-1024,512,-512],[1,-1,2,-3,4,-5,6,-7])):
  gamma=[1048576]*8;f=bytearray(512);w=[]
  for k in range(8):encode(f,256+4*k,xs[k],4);encode(f,288+4*k,gamma[k],4)
  encode(f,416,8,16,False);encode(f,432,17,16,False)
  for k in range(8):
   run(w,'mul_s32_s32',256+4*k,256+4*k,336,8);w.extend(byte(0,336+j,dst=448+j)for j in range(8));run(w,'add_u128',320,448,320,16)
  o=C.invoke(w,'udiv_u128',320,416);w.extend(byte(0,r,dst=352+j)for j,r in enumerate(o['quotient']['refs']))
  run(w,'add_u128',352,432,352,16);run(w,'shl_u128',352,None,352,16,40);run(w,'isqrt_u128',352,None,368,8)
  for k in range(8):run(w,'mul_s32_s32',256+4*k,288+4*k,336,8);run(w,'shl_s64_s128',336,None,448,16,12);run(w,'div_rne_s128_u64_i32',448,368,384+4*k,4)
  save('norm8_chain'+str(i),'norm8_chain',w,f,{'out'+str(k):output(384+4*k,4)for k in range(8)},{'x':list(xs),'gamma':gamma,'epsilon_q24':17,'H':8},source={'kind':'small synthetic complete8-row RMSNorm','limits':'not actual1536hidden or model quality acceptance'})
