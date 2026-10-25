"""Independent full-K matrix and full consumer reference from actual packed payload."""
import argparse,copy,json,hashlib
from pathlib import Path
import numpy as np
from verify import oracle

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rne(n,s):
 if s<0:raise ValueError('unsupported negative physical shift')
 if not s:return n
 q,r=divmod(abs(n),1<<s);q+=2*r>(1<<s)or(2*r==(1<<s)and q%2==1);return -q if n<0 else q

def reference(root,c):
 payload=np.frombuffer((root/c['payload']).read_bytes(),np.uint8).reshape(1536,8,65,16);body=payload[:,:,1:];head=payload[:,:,0]
 acc=(body[:,:,:,:8].view(np.int8).astype(np.int32)*body[:,:,:,8:].view(np.int8).astype(np.int32)).sum(axis=(2,3),dtype=np.int64)
 down=np.empty_like(acc);joined=[]
 for row in range(1536):
  total=0
  for rank in range(8):
   h=head[row,rank].tobytes();mant=int.from_bytes(h[:4],'little',signed=True);shift=31-int.from_bytes(h[4:6],'little',signed=True)-int.from_bytes(h[6:8],'little',signed=True);gate=int.from_bytes(h[8:10],'little');down[row,rank]=rne(int(acc[row,rank])*mant,shift);total+=int(down[row,rank])*gate
  h=head[row,0].tobytes();res=int.from_bytes(h[10:14],'little',signed=True);scale=c['coefficient'];joined.append(rne(rne(total,15)*scale,20)+res)
 gamma=np.frombuffer(bytes.fromhex(c['gamma']),dtype='<i4').astype(int).tolist();st,out=oracle({'h':1536,'x':joined,'gamma':gamma,'epsilon':17})
 if st:raise ValueError('independent norm failed')
 original=json.loads((root/c['original']).read_text())
 result={'acc':acc.reshape(-1).tolist(),'down':down.reshape(-1).tolist(),'joined':joined,'out':out}
 if result['acc']!=sum(original['acc'],[])or result['down']!=sum(original['down'],[])or joined!=original['joined']or out!=original['norm']:raise ValueError('packed actual data differs from original complete chain')
 return result

def check(row,ref):
 for k in('acc','down','joined','out'):
  if row[k]!=ref[k]:raise ValueError('actual integer M consumer '+k)
 if row['status']!=0 or row['M_MACs']!=6291456 or row['M_packets']!=798720 or row['M_store_lines']!=384:raise ValueError('complete K/H/expert execution')
 if row['reads']!=1152 or row['writes']!=384 or row['transactions']!=798720 or row['wire_beats']!=3993600:raise ValueError('finite memory/serialized wire accounting')
 if row['setup_edges']!=768 or row['result_edges']!=768:raise ValueError('actual caller IO')

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();m=json.loads((a.run/'manifest.json').read_text());im=json.loads((a.input/'manifest.json').read_text())
 if m['status']!='RTL_EXECUTED_NOT_RECEIVED'or m['input_manifest_sha256']!=sha(a.input/'manifest.json'):raise ValueError('run binding')
 for root,mf in((a.run,m),(a.input,im)):
  for e in mf['artifacts']:
   if sha(root/e['path'])!=e['sha256']:raise ValueError('actual artifact SHA')
 protocol=json.loads((a.run/'actual.jsonl.protocol.json').read_text())
 if not all(protocol.values()):raise ValueError('actual M reset')
 cases=json.loads((a.input/'cases.json').read_text());rows=[json.loads(s)for s in(a.run/'actual.jsonl').read_text().splitlines()]
 if len(rows)!=6 or len(cases)!=6:raise ValueError('all declared cases')
 summaries=[]
 for c,r in zip(cases,rows):
  if c['name']!=r['name']:raise ValueError('source name')
  ref=reference(a.input,c);check(r,ref);summaries.append({k:v for k,v in r.items()if k not in('acc','down','joined','out')})
 bad=copy.deepcopy(rows[0]);bad['acc'][0]^=1;neg=a.out.with_name(a.out.stem+'-negative.json');neg.write_text(json.dumps(bad))
 try:check(json.loads(neg.read_text()),reference(a.input,cases[0]))
 except ValueError:pass
 else:raise ValueError('rehash semantic negative trusted')
 if a.out.exists():raise ValueError('new out')
 a.out.write_text(json.dumps({'status':'PASS_REAL_M_COMPLETE_CONSUMER','profile':m['profile'],'stall':m['stall'],'cases':6,'protocol':protocol,'source':m['source'],'run_manifest_sha256':sha(a.run/'manifest.json'),'input_manifest_sha256':sha(a.input/'manifest.json'),'rows':summaries,'negative':{'sha256':sha(neg),'status':'REJECTED_AFTER_REHASH'},'scope':'Actual fullK512/all8expert/H1536 down matrix -> RQ -> merge -> residual -> full RMSNorm. Mid-A8, dynamic selectedIDs/gates and earlier model are the frozen external cut. No whole-model or target-PPA claim.'},indent=2)+'\n');print('PASS_REAL_M_COMPLETE_CONSUMER')
if __name__=='__main__':main()
