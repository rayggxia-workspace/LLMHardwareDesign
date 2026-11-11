"""Finite-memory stimuli and exact expected values, independent of candidate RTL."""
import argparse
import hashlib
import json
from pathlib import Path
from numeric import accumulate,input_bytes,packet,physical_read_lines,rne_s32,self_check

def make_case(label,read_delay=0,ack_delay=0,done_hold=0,qualified=False):
 return dict(label=label,read_delay=read_delay,ack_delay=ack_delay,done_hold=done_hold,qualified=qualified,
             memory=bytearray([0x5a]*16384),touched=set(),commands=[],sums={},frontiers={},readbacks={})

def data(c,ctx,ki,total,k,n,shift,first,last,a_addr,b_addr,out_addr,seed_a,seed_b,kind=None):
 a=packet(seed_a,k,n,kind or ('edges' if seed_a%3==0 else 'random'))[0]
 b=packet(seed_b,k,n,kind or ('edges' if seed_b%3==0 else 'random'))[1]
 av,bv=input_bytes(a,b)
 for addr,raw in ((a_addr,av),(b_addr,bv)):
  c['memory'][addr:addr+len(raw)]=raw
 for line in physical_read_lines(a_addr,b_addr,k,n):c['touched'].update(range(line*4,line*4+4))
 c['touched'].update((out_addr//16,out_addr//16+1))
 tag=0x30000000+ctx*101+len(c['label'])
 prior=[0]*n if first else c['sums'][ctx]
 raw=accumulate(a,b,prior);c['sums'][ctx]=raw;c['frontiers'][ctx]=ki+k
 vals=[rne_s32(v,shift) for v in raw];sat=sum(s<<i for i,(_,s) in enumerate(vals))
 packed=sum((v&0xffffffff)<<(32*i) for i,(v,_) in enumerate(vals))
 rawpacked=sum((v&((1<<96)-1))<<(96*i) for i,v in enumerate(raw))
 cmd=dict(ctx=ctx,tag=tag,ki=ki,total=total,k=k,n=n,shift=shift,first=int(first),last=int(last),
          a=a_addr,b=b_addr,out=out_addr,error=0,next=ki+k,sat=sat if last else 0,
          value=packed if last else 0,raw=rawpacked,
          lines=physical_read_lines(a_addr,b_addr,k,n))
 c['commands'].append(cmd)
 if last:
  c['readbacks'][out_addr//16]=packed&((1<<128)-1);c['readbacks'][out_addr//16+1]=packed>>128
 return cmd

def bad(c,template,**changes):
 d=dict(template);d.update(changes);d.update(error=1,next=c['frontiers'].get(d['ctx'],0),sat=0,value=0,raw=0,lines=[])
 c['commands'].append(d)

def suite():
 cases=[]
 for k in (1,7,8,15,16):
  for n in (1,3,8):
   for shift in (0,1,16):
    c=make_case(f'numeric_k{k}_n{n}_s{shift}')
    data(c,0,0,k,k,n,shift,True,True,0,4096+(k+n)%64,12288,24700+k,24900+n)
    cases.append(c)
 for index,value in enumerate((-7,-5,-3,-1,1,3,5,7)):
  c=make_case(f'rne_tie_{value}')
  data(c,0,0,1,1,8,1,True,True,0,4096,12288,index,index,kind='ties')
  cases.append(c)
 for which in ('A_last','B_last','out_last','B_offset63'):
  c=make_case(which);a=16320 if which=='A_last' else 0
  b=16256 if which=='B_last' else 4159 if which=='B_offset63' else 4096
  out=16352 if which=='out_last' else 12288
  data(c,0,0,16,16,8,16,True,True,a,b,out,123,456);cases.append(c)
 c=make_case('invalid_between_valid',done_hold=3)
 first=data(c,0,0,64,16,8,16,True,False,0,4096,12288,100,200)
 for change in (dict(ki=0,first=0),dict(tag=first['tag']+1,ki=16,first=0),
                dict(n=7,ki=16,first=0),dict(n=0,ki=16,first=0),dict(n=9,ki=16,first=0),dict(shift=15,ki=16,first=0),
                dict(total=63,ki=16,first=0),dict(total=0,ki=16,first=0),dict(a=1,ki=16,first=0),
                dict(b=16383,ki=16,first=0),dict(out=12289,ki=16,first=0),
                dict(first=1,ki=0),dict(k=0,first=0,ki=16),dict(k=17,first=0,ki=16),
                dict(ctx=1,first=1,ki=0,out=12288),dict(ctx=1,first=0,ki=0),
                dict(ctx=1,first=1,ki=65535,total=65535,k=1),dict(ctx=1,first=1,ki=0,out=16368)):
  bad(c,first,**change)
 for i in range(1,4):data(c,0,i*16,64,16,8,16,False,i==3,i*64,4096+i*128,12288,100+i,200+i)
 cases.append(c)
 c=make_case('closing_guard',done_hold=128)
 last=data(c,0,0,16,16,8,16,True,True,0,4096,12288,123,456)
 # A guaranteed free completion credit admits this malformed successor before
 # the held final response retires. It cannot reopen the context or write S.
 bad(c,last,tag=last['tag']+1,ki=0,k=16,total=16,first=1,last=1)
 cases.append(c)
 for label,rd,ad,hold,packets in (('read_response_hold4',4,0,0,16),('write_ACK_hold4',0,4,0,16),
                                  ('completion_credit8',0,0,128,20)):
  c=make_case(label,rd,ad,hold)
  for i in range(packets):data(c,0,i*16,packets*16,16,8,16,i==0,i==packets-1,(i%16)*64,
                               4096+(i%16)*128,12288,700+i%16,900+i%16)
  cases.append(c)
 for contexts,total in ((1,2048),(1,11008),(8,2048),(8,11008)):
  c=make_case(f'qualified_ctx{contexts}_K{total}',qualified=True)
  for tile in range(total//256):
   for ctx in range(contexts):
    for p in range(16):
     ki=tile*256+p*16;index=(ki//16)%32 if contexts==1 else p%4
     bindex=index if contexts==1 else ctx*4+index
     data(c,ctx,ki,total,16,8,16,ki==0,ki+16==total,index*64,4096+bindex*128,
          12288+ctx*32,1700+index,1900+bindex)
  cases.append(c)
 return cases

def generate(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);cases=suite();rows=[str(len(cases))];summary=[]
 fields=('ctx','tag','ki','total','k','n','shift','first','last','a','b','out','error','next')
 for case_id,c in enumerate(cases):
  commands=c['commands'];writes=sorted(c['touched']);readbacks=sorted(c['readbacks'].items())
  rows.append(f"{case_id} {len(commands)} {len(writes)} {len(readbacks)} {c['read_delay']} {c['ack_delay']} {c['done_hold']} {int(c['qualified'])}")
  for word in writes:rows.append(f"{word} {int.from_bytes(c['memory'][16*word:16*word+16],'little'):032x}")
  for d in commands:rows.append(' '.join(str(d[k]) for k in fields)+f" {d['sat']:02x} {d['value']:064x} {d['raw']:0192x}")
  for word,val in readbacks:rows.append(f'{word} {val:032x}')
  summary.append(dict(case=case_id,label=c['label'],commands=len(commands),valid=sum(not d['error'] for d in commands),
   invalid=sum(d['error'] for d in commands),read_lines=sum(len(d['lines']) for d in commands),
   write_words=2*sum(not d['error'] and d['last'] for d in commands),contexts=len(c['sums']),
   total_k=max(d['total'] for d in commands),read_delay=c['read_delay'],ack_delay=c['ack_delay'],done_hold=c['done_hold'],
   qualified=c['qualified'],command_fields=[{k:v for k,v in d.items() if k not in ('value','raw')} for d in commands]))
 raw=('\n'.join(rows)+'\n').encode();(out/'vectors.txt').write_bytes(raw)
 report=dict(passed=True,oracle=self_check(),cases=summary,vectors_sha256=hashlib.sha256(raw).hexdigest(),
  scope='Python arbitrary-integer mathematical expectations and finite16KiB initialization; no simulation')
 (out/'vectors.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 r=generate(a.out);print(json.dumps(dict(cases=len(r['cases']),vectors_sha256=r['vectors_sha256'],oracle=r['oracle'])))
