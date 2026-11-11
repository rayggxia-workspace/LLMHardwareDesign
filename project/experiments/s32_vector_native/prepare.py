"""Exact arbitrary-integer S32 oracle, independent of RTL implementation."""
import hashlib,importlib.util,json,random
from collections import Counter
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
old_path=Path(__file__).resolve().parent.parent/'u_queue_native/prepare.py'
spec=importlib.util.spec_from_file_location('legacy_prepare',old_path);legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
LO=-(1<<31);HI=(1<<31)-1
def signed(x):return (x&0xffffffff)-(1<<32) if x&(1<<31) else x&0xffffffff
def pack(xs):return sum((x&0xffffffff)<<(32*i) for i,x in enumerate(xs))
def lanes(w):return [signed(w>>(32*i)) for i in range(4)]
def oracle(op,shift,a,b,c):
 if op>=12 or (op in [7,8] and shift<0):return 0,1,0
 out=[];sat=0
 for i,(x,y,z) in enumerate(zip(a,b,c)):
  if op==0:v=x+y
  elif op==1:v=x-y
  elif op==2:v=x*y
  elif op==3:v=x*y+z
  elif op==4:v=max(x,y)
  elif op==5:v=min(x,y)
  elif op==6:v=x if z else y
  elif op==7:v=x<<shift
  elif op==8:v=x>>shift
  elif op==9:v=x*b[i&2]+(-1 if i%2==0 else 1)*a[i^1]*b[i|1]
  elif op==10:v=x
  else:v=abs(x)
  if op in [2,3,9,10]:
   if shift<0:v<<=-shift
   elif shift>0:
    q,r=divmod(v,1<<shift);v=q+int(2*r>(1<<shift) or (2*r==(1<<shift) and q%2))
  sat|=int(v<LO or v>HI);out.append(min(HI,max(LO,v)))
 return pack(out),0,sat
def prepare(root,out):
 root,out=Path(root),Path(out);out.mkdir(exist_ok=False);previous=legacy.prepare(root,out/'legacy')
 for c in previous['cases']:
  p=out/'legacy'/(c['name']+'-commands.hex');rows=[int(x,16) for x in p.read_text().split()]
  p.write_text(''.join(f'{((x>>308)<<310)|(x&((1<<308)-1)):079x}\n' for x in rows))
 rng=random.Random(2474701);edges=[LO,HI,-1,0,1,-65537,65537,0x40000000,-0x40000000,3,-3,5,-5,32768,-32769]
 dest=out/'s32';dest.mkdir();cases=[]
 for name in ['unary_s32','binary_s32','product_s32','convert_s32','mixed_edges','hazards','direct','backpressure','io_contention']:
  mem=[pack([edges[(i+j)%len(edges)] if i%2==0 else rng.randrange(LO,HI+1) for j in range(4)]) for i in range(1024)];initial=mem.copy();traffic=Counter();rows=[]
  count=2048 if name=='mixed_edges' else 128 if name in ['hazards','direct'] else 64
  for i in range(count):
   op=0;shift=0;src=[i%128,128+i%128];dst=512+i%128;store=True;direct=False;abort=False
   if name=='unary_s32':op=11;src=src[:1]
   if name=='product_s32':op=2;shift=29
   if name=='convert_s32':op=10;shift=[-64,-32,-13,-1,0,1,15,31,34,35,63][i%11];src=src[:1]
   if name=='mixed_edges':
    op=i%16;shift=i//16-64;arity=3 if op in [3,6] else 1 if op in [7,8] or op>=10 else 2
    src=[i%128,128+i%128,256+i%128][:arity];store=i%7!=0
   if name=='hazards':
    op=i%4;shift=29 if op in [2,3] else 0;src=[512+(i-1)%8,512+(i-2)%8];dst=512+i%8
    if op==3:src.append(512+(i-3)%8)
    if i%5==0:dst=src[0]
   if name=='direct':
    op=i%16;shift=i-64;arity=3 if op in [3,6] else 1 if op in [7,8] or op>=10 else 2
    src=[i%128,128+i%128,256+i%128][:arity];direct=True;abort=i%11==0
   dv=pack([edges[(i+j+2)%len(edges)] for j in range(4)]);operands=[0,0,0]
   for j,address in enumerate(src):operands[j]=dv if j==0 and direct else mem[address]
   result,error,sat=(0,1,0) if abort else oracle(op,shift,*(lanes(w) for w in operands))
   if store and not error:mem[dst]=result;traffic['writes']+=1
   traffic['reads']+=0 if abort else len(src)-int(direct)
   command=(op<<310)|((shift&127)<<303)|(len(src)<<301)|(int(store)<<300)|(int(direct)<<299)|(int(abort)<<298)|\
    (sum(a<<(10*j) for j,a in enumerate(src))<<268)|(dst<<258)|(dv<<130)|(error<<129)|(sat<<128)|result
   rows.append(f'{command:079x}')
  for suffix,data in [('initial.hex',[f'{x:032x}' for x in initial]),('final.hex',[f'{x:032x}' for x in mem]),('commands.hex',rows)]:
   (dest/(name+'-'+suffix)).write_text('\n'.join(data)+'\n')
  cases.append(dict(name=name,count=count,stress=int(name in ['direct','hazards','backpressure']),contention=int(name=='io_contention'),traffic=dict(traffic)))
 audit={}
 for name in ['decode512','decode2048','prefill2']:
  ts,ops,tokens=legacy.trace(root/'inputs'/(name+'.trace'));matched=[];excluded=Counter()
  for o in ops:
   arity=1 if o['kind']=='Convert' else 2
   if o['kind'] not in ['Add','Sub','Product','Maximum','Minimum','Convert']:continue
   reason=None
   if o['input_bits']!=[32]*arity or o['output_bits']!=32:reason='width_or_arity'
   elif not -64<=o['shift']<=63:reason='shift'
   elif o['kind'] not in ['Product','Convert'] and o['shift']!=0:reason='nonzero_nonmultiply_shift'
   elif o['elements']%4 or any(ts[t][1]!=o['elements'] for t in o['inputs']):reason='tail_or_broadcast'
   if reason:excluded[reason]+=1
   else:matched.append(o)
  audit[name]=dict(trace_sha256=sha(root/'inputs'/(name+'.trace')),matched=matched,excluded=dict(excluded),values=sum(o['elements'] for o in matched),
   qualification='strict shape/width candidate; arithmetic contract constructed-data tested; no actual graph activation values')
 r=dict(legacy=previous,cases=cases,trace_audit=audit,seed=2474701,numeric_scope='full signed32, signed7 shifts; constructed vectors; not real-model quality',
        generated_sha256={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()})
 (out/'generation.json').write_text(json.dumps(r,indent=2)+'\n');return r
