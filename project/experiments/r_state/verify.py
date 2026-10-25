"""Independent complete-byte receiver: bigint output/state and original72 comparison."""
import argparse,hashlib,json,struct,time,traceback
from pathlib import Path
import numpy as np
from reference import step,Guard
from contracts import CONTRACT
ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',newline='\n')
def check(v,msg):
 if not v:raise ValueError(msg)
def artifacts(p,m):
 names=[]
 for e in m['artifacts']:
  check(set(e)=={'path','bytes','sha256'},'artifact schema');q=p/e['path'];check(q.parent==p and q.is_file(),'artifact path');check(type(e['bytes'])is int and q.stat().st_size==e['bytes']and sha(q)==e['sha256'],'artifact bytes '+str(q));names.append(e['path'])
 check(len(names)==len(set(names)),'duplicate artifacts')
 return names
FIELDS={'schema','index','label','op','status','position','unit','epoch','bank','retries','cycles','reads','writes','s_reads','s_writes','beats','transactions','mul','peer_grants','peer_checked','contested','alpha_bypass','offer_hold','abort_injected','generation','aborts','stale'}
def decode_desc(b):
 w=int.from_bytes(b,'little');check(w&0xffffffff==0x52393901,'descriptor magic');check(w>>123==0 and(w>>119)&15==1 and(w>>118)&1==1,'descriptor contract');u=(w>>96)&65535;u=u-65536 if u>=32768 else u
 return {'position':(w>>32)&0xffffffff,'epoch':(w>>64)&0xffffffff,'unit':u,'bank':(w>>112)&1,'head':(w>>113)&31}
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();started=time.monotonic();receipt={'schema':'r99-receipt-v1','status':'REJECTED','source':json.loads((ROOT/'binding.json').read_text())}
 try:
  for n,h in receipt['source']['sources'].items():check(sha(ROOT/n)==h,'receiver source '+n)
  rm=json.loads((a.run/'manifest.json').read_text());im=json.loads((a.input/'manifest.json').read_text());check(rm['schema']=='r99-run-v1'and rm['task']=='sim'and rm['status']=='RTL_EXECUTED_NOT_RECEIVED','run contract');check(im['schema']=='r99-input-v1'and im['status']=='VERIFIED_COEFFICIENTS_NOT_RTL','input contract');check(rm['input_manifest_sha256']==sha(a.input/'manifest.json'),'input binding');artifacts(a.input,im);artifacts(a.run,rm);check(rm['contract']==CONTRACT and im['contract']==CONTRACT,'precision/IO profile contract');check(im['original_cross_head_wide_guard_events']==[],'cross-head wide guard source')
  for n,h in receipt['source']['sources'].items():
   if n.startswith('project/rtl/')or n.endswith(('/r_sim.cpp','/PROTOCOL.md')):check(rm['source']['sources'].get(n)==h,'executed source '+n)
  check(im['source']['sources']['project/experiments/r_state/inputs.py']==receipt['source']['sources']['project/experiments/r_state/inputs.py'],'input extraction source')
  if rm['mode']=='boundary':
   from verify_boundary import receive_boundary
   receipt.update(receive_boundary(a.run,a.input,rm,im));receipt.update(stall=rm['stall'],contract=CONTRACT,run_source=rm['source']);receipt.update(run_manifest_sha256=sha(a.run/'manifest.json'),input_manifest_sha256=sha(a.input/'manifest.json'));return
  h=rm['head'];head=next(x for x in im['heads']if x['head']==h);image=(a.input/f'head{h}.bin').read_bytes();check(len(image)==1<<20,'input size');old=np.load(a.input/f'head{h}-old.npz',allow_pickle=False)
  rows=[json.loads(s)for s in(a.run/'actual.jsonl').read_text().splitlines()];raw=(a.run/'actual.bin').read_bytes();check(len(raw)==len(rows)*(16+32768*4+128*4),'complete snapshots');state=[0]*32768;y=[0]*128;unit=head['initial_unit'];epoch=0;position=0;bank=0;completed=0;retries=0;totals={k:0 for k in ['cycles','reads','writes','s_reads','s_writes','transactions','beats','mul','alpha_bypass']}
  for i,row in enumerate(rows):
   check(set(row)==FIELDS and row['schema']=='r99-row-v1'and row['index']==i,'row exact schema')
   for k,v in row.items():
    if k not in {'schema','label','abort_injected','generation','aborts','stale'}:check(type(v)is int,'row integer '+k)
   check(type(row['abort_injected'])is bool,'row bool');check(row['beats']==5*row['transactions']and row['transactions']==row['reads']+row['writes'],'five 128bit beats/transaction');check(row['contested']<=row['mul']+row['peer_grants'],'arbitration bounded')
   if row['op']==0:check(i==0 and row['status']==0,'INIT');check(row['writes']==8225 and row['reads']==0,'real INIT cost')
   elif row['op']==1 and row['status']==0 or row['label']=='restore-hardcommit':
    t=position;off=0xb0000+t*2592;magic,pos,hh,res,dt,alpha,skip,res1=struct.unpack_from('<IIIIiIiI',image,off);check((magic,pos,hh,res,res1)==(0x52393943,t,h,0,0),'coefficient metadata')
    coeff=struct.unpack_from('<640i',image,off+32);state,y,unit,epoch,retry=step(state,unit,epoch,coeff[:128],coeff[128:384],coeff[384:],dt,alpha,skip);check(row['label']=='restore-hardcommit'or row['retries']==retry,'complete-head retry count');retries+=retry;position+=1;bank^=1;completed+=1
    check(np.array_equal(np.array(y,np.int32),old['scan'][t]),'original72 readout');check(unit==int(old['units'][position]),'original72 selected-head units')
    check(row['label']=='restore-hardcommit'or(row['reads']==41122+retry*16384 and row['writes']==32801+retry*24576),'full bounded external traffic');expected_mul=(98688 if alpha!=1<<31 else 65920)+retry*(65792 if alpha!=1<<31 else 33024);check(row['label']=='restore-hardcommit'or row['mul']==expected_mul,'actual S32 inventory cycles')
   elif row['op']==1 and row['status']in(2,3):check(row['abort_injected']==(row['status']==2),'abort/reject provenance')
   elif row['op']==2:check(row['status']==0 and row['reads']==1 and row['writes']==0,'real RESTORE')
   else:raise ValueError('unexpected command/status')
   b=raw[i*131600:(i+1)*131600];desc=decode_desc(b[:16]);check(desc=={'position':position,'epoch':epoch,'unit':unit,'bank':bank,'head':h},'published descriptor versus independent reference');check(row['position']==position and row['epoch']==epoch and row['unit']==unit and row['bank']==bank,'public mirrored context');actual=list(struct.unpack_from('<32768i',b,16));actual_y=list(struct.unpack_from('<128i',b,16+32768*4));check(actual==state,'all 32768 published state codes');check(actual_y==y,'all128 readout codes')
   for k in totals:totals[k]+=row[k]
  if rm['mode']=='protocol':
   from verify_boundary import receive_protocol
   receipt['protocol']=receive_protocol(a.run,rows);check(completed==2 and len(rows)==31,'protocol coverage')
  if rm['mode']=='real':check(all(v['aborts']==0 and v['stale']==0 for v in rows),'real protocol counters');check(completed==72 and len(rows)==82,'all72 plus9restore+init');check(np.array_equal(np.array(state,np.int32).reshape(128,256),old['final']),'original72 final state');check(epoch==head['rescale_events_from_original_unit_trace'],'head local epoch')
  receipt.update(status='PASS_FULL_HEAD_RTL_BIGINT',run_manifest_sha256=sha(a.run/'manifest.json'),input_manifest_sha256=sha(a.input/'manifest.json'),rows=len(rows),committed_steps=completed,head_local_numeric_epoch=epoch,original32head_epoch=im['old_global_epoch'],retries=retries,totals=totals,external_payload_bytes=totals['transactions']*16,external_wire_bytes=totals['transactions']*5*16,transport_sideband='32bit generation request and response; serialization unspecified, excluded from 5beats',all_state_codes_compared=len(rows)*32768,all_readout_codes_compared=len(rows)*128,mode=rm['mode'],stall=rm['stall'],contract=CONTRACT,run_source=rm['source'])
 except Exception as e:receipt.update(error=str(e),traceback=traceback.format_exc());raise
 finally:receipt['seconds']=time.monotonic()-started;put(a.out,receipt)
 print(receipt['status'])
if __name__=='__main__':main()
