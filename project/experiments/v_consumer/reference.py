"""Independent integer oracle from original74 gate/up, not the executable's intermediates."""
import argparse,hashlib,json,math,struct
from pathlib import Path
import numpy as np
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(v,s):
 if not v:raise ValueError(s)
def bound(root):
 m=json.loads((root/'manifest.json').read_text())
 for e in m['artifacts']:require(sha(root/e['path'])==e['sha256'],'source SHA '+e['path'])
 return m
def rne(n,s):
 require(s>=0,'nonnegative physical shift')
 q,r=divmod(abs(int(n)),1<<s);q+=2*r>(1<<s)or(2*r==(1<<s)and q%2);return -q if n<0 else q
def v_reference(g,u,lut):
 mid=[];codes=[];deltas=[];lookups=0
 for gr,ur in zip(g,u):
  row=[]
  for x,y in zip(gr,ur):
   x=int(x);y=int(y)
   if x< -131072:a=0
   elif x>131072:a=x
   else:a=int(lut[rne(x+131072,4)]);lookups+=1
   m=rne(a*y,12)
   if not -(1<<31)<=m<(1<<31):raise OverflowError('MID Q12 does not fit I32')
   row.append(m)
  maximum=max(abs(x)for x in row);delta=next(d for d in range(26)if rne(maximum,d)<=127)
  aa=[rne(x,delta)for x in row];require(all(-127<=x<=127 for x in aa),'symmetric A8');mid+=row;codes+=aa;deltas.append(delta)
 return {'mid':mid,'A8':codes,'delta':deltas,'lut_reads':lookups}
def reference(root,c):
 if c.get('source')=='synthetic-original-gateup-boundaries':
  gu=np.frombuffer((root/c['gateup']).read_bytes(),dtype='<i4').reshape(8,2,512);lut=np.frombuffer((root/'lut.bin').read_bytes()[:65540],dtype='<i4');return v_reference(gu[:,0],gu[:,1],lut)
 compiled=Path(c['compiled']);runtime=Path(c['runtime']);bound(compiled);bound(runtime)
 require(sha(runtime/'runtime.npz')==c['runtime_sha256'],'bound original runtime');require(sha(compiled/'manifest.json')==c['compiled_manifest_sha256'],'bound original constants')
 with np.load(compiled/'constants.npz',allow_pickle=False)as const,np.load(runtime/'runtime.npz',allow_pickle=False)as z:
  L=c['layer'];t=c['token'];g=z['expert_gate_q12'][t];u=z['expert_up_q12'][t];ref=v_reference(g,u,const['silu_lut_q12']);require(np.array(ref['mid']).reshape(8,512).tolist()==z['expert_mid_q12'][t].tolist(),'original MID unchanged');require(ref['A8']==z['mid_a8'][t].reshape(-1).tolist(),'original runtime A8 unchanged');require(ref['delta']==z['mid_delta'][t].tolist(),'original minimum delta unchanged')
  gu=np.stack([g,u],axis=1).astype('<i4').tobytes();require(gu==(root/c['gateup']).read_bytes(),'actual input only original gate/up')
  ids=z['router.ids'][t];require(ids.tolist()==c['ids'],'original selected experts');w=const[f'L{L}.down_w8'][ids];mant=const[f'L{L}.down_mant_q31'][ids];exp=const[f'L{L}.down_exp'][ids];head=np.frombuffer((root/c['records']).read_bytes(),np.uint8).reshape(1536,8,33,16)
  require(head[:,:,1:].copy().view(np.int8).reshape(1536,8,512).tolist()==w.transpose(1,0,2).tolist(),'all physical W8 unchanged')
  aa=np.array(ref['A8'],np.int64).reshape(8,512);acc=(w.astype(np.int64)*aa[:,None,:]).sum(axis=2);down=np.empty_like(acc);joined=[]
  for row in range(1536):
   total=0
   for rank in range(8):
    physical=struct.unpack('<ihhHiH',head[row,rank,0].tobytes());expected=(int(mant[rank,row]),int(exp[rank,row]),0,int(z['router.gate_q15'][t,rank]),int(z['residual_q12'][t,row]),0);require(physical==expected,'static metadata unchanged / old host delta absent')
    down[rank,row]=rne(int(acc[rank,row])*int(mant[rank,row]),31-int(exp[rank,row])-ref['delta'][rank]);require(-(1<<31)<=down[rank,row]<(1<<31),'down I32');total+=int(down[rank,row])*expected[3]
   merged=rne(total,15);scaled=rne(merged*c['coefficient'],20);joined.append(scaled+int(z['residual_q12'][t,row]))
  gg=const[f'L{L}.next_gamma_q20'].astype('<i4');require(gg.tobytes()==(root/c['gamma']).read_bytes(),'original gamma');sumsq=sum(v*v for v in joined);den=math.isqrt((sumsq//1536+17)<<40);output=[]
  for v,gv in zip(joined,gg):
   n=v*int(gv)*4096;q,r=divmod(abs(n),den);q+=2*r>den or(2*r==den and q%2);output.append(-q if n<0 else q)
  for a,b in [(acc,z['down_acc32'][t]),(down,z['down_q12'][t])]:require(a.tolist()==b.tolist(),'original full-K trace unchanged')
  require(joined==z['layer_output_q12'][t].tolist()and output==z['next_norm_q12'][t].tolist(),'original full consumer unchanged')
  ref.update(acc=acc.T.reshape(-1).tolist(),down=down.T.reshape(-1).tolist(),joined=joined,out=output,sum_hex=f'{sumsq:032x}',den_hex=f'{den:032x}');return ref

def check(row,ref):
 for k in ('mid','A8','delta'):
  require(type(row[k])is list and all(type(x)is int for x in row[k]),'integer typed '+k)
  require(row[k]==ref[k],'actual RTL '+k)
 counts={'gate_reads':1024,'up_reads':1024,'lut_reads':ref['lut_reads'],'v_sreads':1024,'v_swrites':1280}
 if not row['prep_only']:
  for k in ('acc','down','joined','out','sum_hex','den_hex'):require(row[k]==ref[k],'actual full consumer '+k)
  counts.update(M_packets=405504,M_MACs=6291456,M_writes=384,cache_reads=393216,cache_writes=0,norm_reads=1152,norm_writes=768,gamma_loads=384,gamma_stores=384,den_events=1)
  counts.update(transactions=2048+ref['lut_reads']+405504+384,mul_grants0=26112,mul_grants1=7168)
 else:
  require(not row['acc']and not row['down']and not row['joined']and not row['out'],'no host consumer in prep-only')
  counts.update(transactions=2048+ref['lut_reads'],mul_grants0=0,mul_grants1=4096)
 counts['wire_beats']=5*counts['transactions']
 for k,v in counts.items():require(type(row[k])is int and row[k]==v,'actual count '+k+': '+str(row[k])+' != '+str(v))
 require(row['status']==0,'success status');return {k:v for k,v in row.items()if k not in ('mid','A8','delta','acc','down','joined','out')}

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();im=bound(a.input);m=bound(a.run);require(m['status']=='RTL_EXECUTED_NOT_RECEIVED'and m['input_manifest_sha256']==sha(a.input/'manifest.json'),'run input binding');cs=json.loads((a.input/'cases.json').read_text());lookup={c['name']:c for c in cs};rows=[json.loads(x)for x in(a.run/'actual.jsonl').read_text().splitlines()];refs={};summaries=[]
 for row in rows:
  if row['name']not in refs:refs[row['name']]=reference(a.input,lookup[row['name']])
  summaries.append(check(row,refs[row['name']]))
 require(len(rows)==(2 if m['pilot']else 6),'expected actual cases');a.out.write_text(json.dumps({'status':'PASS_INDEPENDENT_ORIGINAL_GATEUP_FULL_CONSUMER','source':m['source'],'run_manifest_sha256':sha(a.run/'manifest.json'),'input_manifest_sha256':sha(a.input/'manifest.json'),'rows':summaries},indent=2)+'\n');print('PASS_INDEPENDENT_ORIGINAL_GATEUP_FULL_CONSUMER')
if __name__=='__main__':main()
