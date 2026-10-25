"""Independent full-K matrix and full consumer reference from actual packed payload."""
import argparse,copy,json,hashlib
from pathlib import Path
import numpy as np
from norm_reference import oracle

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rne(n,s):
 if s<0:raise ValueError('unsupported negative physical shift')
 if not s:return n
 q,r=divmod(abs(n),1<<s);q+=2*r>(1<<s)or(2*r==(1<<s)and q%2==1);return -q if n<0 else q

def reference(root,c,cache=0):
 raw=(root/c[f'payload{cache}']).read_bytes()
 if cache:
  aa=np.frombuffer(raw[:4096],np.int8).reshape(8,512).astype(np.int32);payload=np.frombuffer(raw[4096:],np.uint8).reshape(1536,8,33,16);head=payload[:,:,0];ww=payload[:,:,1:].copy().view(np.int8).reshape(1536,8,512).astype(np.int32);acc=(aa*ww).sum(axis=2,dtype=np.int64)
 else:
  payload=np.frombuffer(raw,np.uint8).reshape(1536,8,65,16);body=payload[:,:,1:];head=payload[:,:,0]
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

def check(row,ref,cache=0):
 packets=405760 if cache else 798720
 for k in('acc','down','joined','out'):
  if row[k]!=ref[k]:raise ValueError('actual integer M consumer '+k)
 if row['status']!=0 or row['M_MACs']!=6291456 or row['M_packets']!=packets or row['M_store_lines']!=384:raise ValueError('complete K/H/expert execution')
 if row['reads']!=1152 or row['writes']!=384 or row['transactions']!=packets or row['wire_beats']!=packets*5:raise ValueError('finite memory/serialized wire accounting')
 if row['cache_reads']!=(393216 if cache else 0)or row['cache_writes']!=(256 if cache else 0):raise ValueError('finite shared A store')
 if row['mul_grants0']!=26112 or row['mul_grants1']!=3072 :raise ValueError('actual common multiplication workload')
 if row['setup_edges']!=768 or row['result_edges']!=768:raise ValueError('actual caller IO')

def protocol_check(p):
 keys=('mode_parameter_latching','cfg_command_competition','held_done_response','stage_abort_restart','error_recovery','stale_epoch_discard','coordinated_reset_restart')
 if not isinstance(p,dict) or set(p)!=set(keys)|{'schema','commands_accepted','abort_stages','error_conditions','blocked_command_edges','held_done_edges','full_output_commands'} or p.get('schema')!='runtime85-protocol-v1' or any(p.get(k) is not True for k in keys):raise ValueError('protocol required typed fields')
 expected={'commands_accepted':47,'abort_stages':10,'error_conditions':6,'blocked_command_edges':36,'held_done_edges':144,'full_output_commands':30}
 for k,v in expected.items():
  if type(p.get(k)) is not int or p[k]!=v:raise ValueError('protocol counts '+k)
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();m=json.loads((a.run/'manifest.json').read_text());im=json.loads((a.input/'manifest.json').read_text())
 if m['status']!='RTL_EXECUTED_NOT_RECEIVED' or m['input_manifest_sha256']!=sha(a.input/'manifest.json') or type(m['profile'])is not int or m['profile']!=0 or type(m['stall'])is not int or m['stall']not in(0,1):raise ValueError('run binding')
 for root,mf in((a.run,m),(a.input,im)):
  for ent in mf['artifacts']:
   if sha(root/ent['path'])!=ent['sha256']:raise ValueError('actual artifact SHA')
 old=Path(im['old_root']);
 if old!=Path('/public/home/yuzelu/RuizhiLiang/issue84-cache-share-20261025/input01'):raise ValueError('explicit reused84 root')
 om=json.loads((old/'manifest.json').read_text())
 if sha(old/'manifest.json')!=im['old_manifest_sha256']:raise ValueError('reused84 binding')
 for ent in om['artifacts']:
  if sha(old/ent['path'])!=ent['sha256']:raise ValueError('original physical payload SHA')
 protocol=json.loads((a.run/'actual.jsonl.protocol.json').read_text());protocol_check(protocol)
 rows=[json.loads(s)for s in(a.run/'actual.jsonl').read_text().splitlines()];cases=json.loads((a.input/'cases.json').read_text())
 if len(rows)!=30 or len(cases)!=6:raise ValueError('full command cardinality')
 lookup={c['name']:c for c in cases};refs={(c['name'],v):reference(old,c,v)for c in cases for v in(0,1)};summaries=[];seen=set();mixed=set()
 for row in rows:
  if type(row.get('cache'))is not int or row['cache']not in(0,1):raise ValueError('mode')
  ident=(row['name'],row['cache'],row['role'])
  if ident in seen:raise ValueError('duplicate command')
  seen.add(ident);check(row,refs[row['name'],row['cache']],row['cache'])
  if row['role']=='mixed':mixed.add((row['name'],row['cache']))
  summaries.append({k:v for k,v in row.items()if k not in('acc','down','joined','out')})
 if mixed!=set(refs):raise ValueError('both runtime modes all6 real cases')
 expected_roles={'mixed','restart-stale-epoch','restart-hard-reset'}|{'restart-stage-'+str(i)for i in range(1,11)}|{'restart-error-'+str(v)+'-'+str(f)for v in(0,1)for f in(1,2,3)}
 if {x['role']for x in rows}!=expected_roles:raise ValueError('missing recovery')
 neg=copy.deepcopy(rows[0]);neg['acc'][0]^=1;np=a.out.with_name(a.out.stem+'-negative.json');np.write_text(json.dumps(neg))
 try:check(json.loads(np.read_text()),refs[neg['name'],neg['cache']],neg['cache'])
 except ValueError:pass
 else:raise ValueError('semantic corruption accepted')
 negatives=[{},dict(protocol,mode_parameter_latching='true'),{k:v for k,v in protocol.items()if k!='stage_abort_restart'},dict(protocol,commands_accepted=46),dict(protocol,unknown=True)]
 for bad in negatives:
  try:protocol_check(bad)
  except ValueError:pass
  else:raise ValueError('bad protocol accepted')
 if a.out.exists():raise ValueError('new receipt only')
 a.out.write_text(json.dumps({'status':'PASS_RUNTIME_MODES_RECOVERY','commands':30,'source':m['source'],'run_manifest_sha256':sha(a.run/'manifest.json'),'input_manifest_sha256':sha(a.input/'manifest.json'),'stall':m['stall'],'protocol':protocol,'rows':summaries,'semantic_negative_sha256':sha(np),'metadata_negative_cases':5},indent=2)+'\n');print('PASS_RUNTIME_MODES_RECOVERY')
if __name__=='__main__':main()
