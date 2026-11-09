"""Unbounded Python dot oracle, RNE and finite-packet RTL transcript."""
from pathlib import Path
import argparse,hashlib,json,random

def quantize(value,shift):
 q,r=divmod(value,1<<shift)
 if shift and (r*2>(1<<shift) or (r*2==(1<<shift) and q%2)):q+=1
 return max(-(1<<31),min((1<<31)-1,q)),int(q<-(1<<31) or q>(1<<31)-1)

def generate(root,lanes):
 root=Path(root);root.mkdir(exist_ok=False);rng=random.Random(2401024);jobs=[];expected=[];lines=[]
 for length in [1,7,8,15,16,17,31,32,127,256,1025,2048,11008]:
  for bits in [8,16,32]:
   for n in [1,3,8]:
    row=len(jobs)%8;shift=[0,16,31,63][len(jobs)%4]
    a=[rng.randrange(-(1<<31),1<<31) for _ in range(length)]
    b=[[rng.randrange(-(1<<(bits-1)),1<<(bits-1)) for _ in range(length)] for _ in range(n)]
    if length>=2:a[:2]=[-(1<<31),(1<<31)-1]
    packets=[]
    for start in range(0,length,lanes):
     k=min(lanes,length-start);av=sum((a[start+i]&0xffffffff)<<(32*i) for i in range(k))
     for part in range(bits//8):
      bv=sum(((b[j][start+i]>>(part*8))&255)<<(8*(j*lanes+i)) for j in range(n) for i in range(k))
      first=start==0 and part==0;last=start+k==length and part==bits//8-1
      packets.append((f'{row} {int(first)} {int(last)} {k} {n} {shift} {part*8} {int(part<bits//8-1)} {av:0{lanes*8}x} {bv:0{lanes*16}x}',last))
    values=[quantize(sum(x*y for x,y in zip(a,weights)),shift) for weights in b]
    data=sum((v&0xffffffff)<<(32*j) for j,(v,s) in enumerate(values));sat=sum(s<<j for j,(v,s) in enumerate(values))
    jobs.append(dict(packets=packets,expected=dict(row=row,error=0,sat=sat,data=f'{data:064x}'),length=length,bits=bits,n=n))
 # Round-robin packet issue across eight independent row contexts.
 for base in range(0,len(jobs),8):
  group=jobs[base:base+8]
  for i in range(max(len(j['packets']) for j in group)):
   for job in group:
    if i<len(job['packets']):
     line,last=job['packets'][i];lines.append(line)
     if last:expected.append(job['expected'])
 # Explicit illegal continuation and malformed packets, with error outputs.
 for row,k,n,bs in [(0,1,8,0),(1,0,8,0),(2,1,0,0),(3,1,8,7)]:
  lines.append(f'{row} 0 0 {k} {n} 0 {bs} 0 0 0')
  expected.append(dict(row=row,error=1,sat=0,data='0'*64))
 raw=(str(len(lines))+'\n'+'\n'.join(lines)+'\n').encode();(root/'m-input.txt').write_bytes(raw)
 report=dict(k_lanes=lanes,dots=len(jobs),packets=len(lines),expected=expected,
  stimulus_sha256=hashlib.sha256(raw).hexdigest(),scope='exact byte-plane reconstruction, full-K RNE, row contexts, tails, errors and output stalls; no physical qualification')
 (root/'oracle.json').write_text(json.dumps(report,indent=2)+'\n')
 print('VECTORS_READY',lanes,len(lines),len(expected))

def verify(root):
 root=Path(root);expected=json.loads((root/'oracle.json').read_text());actual=[]
 for line in (root/'rtl.log').read_text().splitlines():
  if line.startswith('M_RESULT '):
   _,index,row,error,sat,data=line.split();assert int(index)==len(actual)
   actual.append(dict(row=int(row),error=int(error),sat=int(sat,16),data=f'{int(data,16):064x}'))
 assert actual==expected['expected'],next(((i,a,e) for i,(a,e) in enumerate(zip(actual,expected['expected'])) if a!=e),('length mismatch',len(actual),len(expected['expected'])))
 (root/'verification.json').write_text(json.dumps(dict(passed=True,k_lanes=expected['k_lanes'],responses=len(actual),packets=expected['packets'],scope=expected['scope']),indent=2)+'\n')
 print('M_ORACLE_PASS',expected['k_lanes'],len(actual))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['generate','verify']);p.add_argument('root');p.add_argument('--lanes',type=int,default=16);a=p.parse_args()
 generate(a.root,a.lanes) if a.mode=='generate' else verify(a.root)
