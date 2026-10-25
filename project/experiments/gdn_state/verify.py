"""Independent strict complete-command, full-state/output and stage receiver."""
import argparse,hashlib,json,struct
from pathlib import Path
import numpy as np
from contracts import CONTRACT
from reference import step,observations
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ROW=set('schema index label op slot status position version units_raw epoch bank generation state_validated aborts stale retries cycles reads writes s_reads s_writes beats transactions mul wide_calls peer_grants peer_checked contested alpha_bypass offer_hold abort_injected'.split())
SNAP=16+64+131072+2048

def check_artifacts(root,m):
 seen=set()
 for x in m['artifacts']:
  assert set(x)=={'path','sha256','bytes'}and isinstance(x['path'],str)and Path(x['path']).name==x['path']and x['path']not in seen,'artifact schema/path'
  seen.add(x['path']);p=root/x['path'];assert p.stat().st_size==x['bytes']and sha(p)==x['sha256'],'artifact bytes/hash'
 return seen

def snapshot(data):
 assert len(data)==SNAP
 rt=int.from_bytes(data[:16],'little');meta=[int.from_bytes(data[16+16*i:32+16*i],'little')for i in range(4)]
 assert rt&0xffffffff==0x47445231 and(rt>>33)&1 and(rt>>34)&((1<<30)-1)==0,'root'
 bank=(rt>>32)&1;ver=rt>>64
 m0,m1,m2,m3=meta
 assert m0&0xffffffff==0x47444e31 and(m0>>32)&65535==1 and(m0>>48)&0xffffffff==182389313,'metadata identity'
 assert(m0>>80)&31==0 and(m0>>85)&31==1 and(m0>>90)&63==0,'group'
 assert(m2>>32)&((1<<64)-1)==104 and(m2>>96)&1==bank and m2>>97==0,'metadata context'
 assert [m3>>(32*i)&0xffffffff for i in range(4)]==[0x040b0000,32,0x04000000+bank*131072,0x040a0000+bank*2048],'metadata address'
 assert m1>>64==ver,'root/meta version'
 units=np.frombuffer(((m0>>96)&65535).to_bytes(2,'little'),dtype=np.int8).astype(int).tolist();vu=np.frombuffer((m0>>112).to_bytes(2,'little'),dtype=np.int8).astype(int).tolist()
 return {'state':np.frombuffer(data[80:131152],dtype='<i4').reshape(2,128,128),'y':np.frombuffer(data[131152:],dtype='<i8').reshape(2,128),'units':units,'value_units':vu,'epoch':m2&0xffffffff,'position':m1&((1<<64)-1),'version':ver,'bank':bank}

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 rm=json.loads((a.run/'manifest.json').read_text());im=json.loads((a.input/'manifest.json').read_text());assert rm['schema']=='gdn104-run-v1'and rm['status']=='RTL_EXECUTED_NOT_RECEIVED'and rm['contract']==im['contract']==CONTRACT
 assert im['schema']=='gdn104-input-v1'and im['status']=='VERIFIED_COEFFICIENTS_NOT_RTL'and sha(a.input/'manifest.json')==rm['input_manifest_sha256']
 assert {'actual.bin','actual.jsonl','stages.bin','protocol.jsonl'}<=check_artifacts(a.run,rm);check_artifacts(a.input,im)
 with np.load(a.input/'coefficients.npz',allow_pickle=False)as n:z={k:n[k].copy()for k in n.files}
 rows=[json.loads(x)for x in(a.run/'actual.jsonl').read_text().splitlines()];raw=(a.run/'actual.bin').read_bytes();stage_data=(a.run/'stages.bin').read_bytes();assert len(raw)==len(rows)*SNAP and len(stage_data)%40==0
 stage_rows={};stage_count=0
 for off in range(0,len(stage_data),40):
  record,*rest=struct.unpack_from('<6I2q',stage_data,off);assert record<len(rows),'stage command';stage_rows.setdefault(record,[]).append(tuple(rest));stage_count+=1
 state=z['state_initial'].copy();y=np.zeros((2,128),dtype=np.int64);units=list(map(int,z['state_units']));vu=list(map(int,z['value_units']));ep=im['epoch'];pos=im['position'];ver=im['version'];bank=0;commits=0;totals={k:0 for k in('cycles','reads','writes','s_reads','s_writes','beats','transactions','mul','wide_calls','alpha_bypass')};retry_count=0;checked_stages=0;status_counts={}
 for index,row in enumerate(rows):
  assert set(row)==ROW and row['schema']=='gdn104-row-v1'and row['index']==index,'row schema/index'
  for k in ROW-{'schema','label','abort_injected'}:assert type(row[k])is int and row[k]>=0,(k,'integer type')
  assert type(row['label'])is str and type(row['abort_injected'])is bool
  assert row['transactions']==row['reads']+row['writes']and row['beats']==row['transactions']*5,'physical link contract'
  assert row['status']in(0,2,3,4,6,7,8,9,10,11,12),'status'
  status_counts[str(row['status'])]=status_counts.get(str(row['status']),0)+1
  slot=row['slot'];committed=row['op']==1 and row['status']==0 or row['label']=='restore-hardcommit'
  has_calc=row['op']==1 and row['status']in(0,2,3)or row['label']=='restore-hardcommit'
  if row['label']=='restore-hardcommit':slot=ver-im['version']
  if has_calc:
   result=step(state,z['q'][slot],z['k'][slot],z['v'][slot],z['decay'][slot],z['beta'][slot],units,vu,ep);ns,ny,nu,ne,attempts=result
   wanted=observations(attempts);actual=stage_rows.get(index,[])
   for actual_stage in actual:
    assert actual_stage==next(wanted,None),(index,'independent stage mismatch',actual_stage)
   checked_stages+=len(actual)
   if committed or row['status']==3:assert next(wanted,None)is None,(index,'missing stage')
   if committed:state,y,units,ep=ns,ny,nu,ne;pos+=1;ver+=1;bank=1-bank;commits+=1;retry_count+=len(attempts)-1
  else:assert not stage_rows.get(index),('unexpected stages',index)
  sn=snapshot(raw[index*SNAP:(index+1)*SNAP]);assert np.array_equal(sn['state'],state)and np.array_equal(sn['y'],y),(index,'independent numerical mismatch')
  for k,v in [('units',units),('value_units',vu),('epoch',ep),('position',pos),('version',ver),('bank',bank)]:assert sn[k]==v,(index,k,sn[k],v)
  assert(row['position'],row['version'],row['epoch'],row['units_raw'],row['bank'])==(pos,ver,ep,(units[0]&255)|((units[1]&255)<<8),bank),'DUT published metadata'
  if row['op']==1 and row['status']==0:assert row['retries']==len(attempts)-1 and row['offer_hold']>=8 and row['state_validated']==1,'commit protocol'
  for k in totals:totals[k]+=row[k]
 if rm['mode']=='real':assert commits==rm['steps']==im['steps']and all(x['status']==0 for x in rows),'complete profile'
 if rm['mode']=='protocol':assert status_counts.get('2')==14 and status_counts.get('3')==1 and commits==2,'complete recovery count'
 receipt={'schema':'gdn104-receipt-v1','status':'PASS_COMPLETE_INTEGER_RTL_NOT_PPA','contract':CONTRACT,'run_manifest_sha256':sha(a.run/'manifest.json'),'input_manifest_sha256':sha(a.input/'manifest.json'),'receiver_sha256':sha(__file__),'reference_sha256':sha(Path(__file__).with_name('reference.py')),'source':rm['source'],'profile':im['profile'],'mode':rm['mode'],'stall':rm['stall'],'commands':len(rows),'commits':commits,'range_waves':retry_count,'complete_state_cells_checked':len(rows)*32768,'complete_output_codes_checked':len(rows)*256,'stage_pairs_checked':checked_stages,'status_counts':status_counts,'totals':totals,'final':{'position':pos,'version':ver,'units':units,'epoch':ep,'bank':bank},'limits':['standalone GDN; no shared M/A/V integration','no physical macro/PPA','consumer accept external contract; no full gated norm','32 finite coefficient slots; not full256']}
 assert checked_stages==stage_count
 (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf8',newline='\n');print(json.dumps(receipt))
if __name__=='__main__':main()
