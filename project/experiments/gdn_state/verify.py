"""Independent strict complete-command, full-state/output and stage receiver."""
import argparse,hashlib,json,struct,re
from pathlib import Path
import numpy as np
from contracts import CONTRACT
from reference import step,observations,Refusal
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ROW=set('schema index label op slot status position version units_raw epoch bank generation state_validated aborts stale retries cycles reads writes s_reads s_writes beats transactions mul wide_calls peer_grants peer_checked contested alpha_bypass offer_hold abort_injected'.split())
SNAP=16+64+131072+2048

def check_artifacts(root,m):
 seen=set()
 for x in m['artifacts']:
  assert type(x.get('bytes'))is int and x['bytes']>=0 and isinstance(x.get('sha256'),str)and re.fullmatch('[0-9a-f]{64}',x['sha256']),'artifact typed descriptor'
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
 rm=json.loads((a.run/'manifest.json').read_text());im=json.loads((a.input/'manifest.json').read_text());assert rm['schema']=='gdn104-run-v1'and rm['status']in('RTL_EXECUTED_NOT_RECEIVED','GATE_EXECUTED_NOT_RECEIVED')and json.dumps(rm['contract'],sort_keys=True)==json.dumps(im['contract'],sort_keys=True)==json.dumps(CONTRACT,sort_keys=True)
 assert set(rm)==({'contract','schema','status','source','task','stall','steps','first_slot','mode','input_manifest_sha256','build_manifest_sha256','artifacts'}|({'implementation','prepared_manifest_sha256','case'}if rm['status']=='GATE_EXECUTED_NOT_RECEIVED'else set())),'exact run schema'
 assert set(rm['source'])=={'commit','sources'}and re.fullmatch('[0-9a-f]{40}',rm['source']['commit']),'source binding schema'
 assert all(isinstance(n,str)and re.fullmatch('[0-9a-f]{64}',h)for n,h in rm['source']['sources'].items()),'source SHA'
 assert all(type(rm[k])is int for k in ('stall','steps','first_slot'))and rm['stall']in(0,1)and 0<rm['steps']<=32 and 0<=rm['first_slot']<32,'typed run bounds'
 assert rm['task']=='sim'and rm['mode']in('real','protocol','fixture','checkpoint'),'run task/mode'
 if rm['status']=='GATE_EXECUTED_NOT_RECEIVED':assert rm['implementation']=='gate'and rm['mode']=='checkpoint','gate scope'
 assert im['schema']=='gdn104-input-v1'and im['status']=='VERIFIED_COEFFICIENTS_NOT_RTL'and sha(a.input/'manifest.json')==rm['input_manifest_sha256']
 assert {'actual.bin','actual.jsonl','stages.bin','protocol.jsonl'}<=check_artifacts(a.run,rm);check_artifacts(a.input,im)
 with np.load(a.input/'coefficients.npz',allow_pickle=False)as n:z={k:n[k].copy()for k in n.files}
 image=(a.input/'image.bin').read_bytes();assert len(image)==1<<20,'finite image'
 initial_bank=im.get('bank',0);assert initial_bank in(0,1)
 initial=snapshot(image[0xa1080:0xa1090]+image[0xa1000+initial_bank*64:0xa1040+initial_bank*64]+image[initial_bank*131072:(initial_bank+1)*131072]+image[0xa0000+initial_bank*2048:0xa0800+initial_bank*2048])
 assert np.array_equal(initial['state'],z['state_initial'])and initial['units']==list(map(int,z['state_units']))and initial['value_units']==list(map(int,z['value_units']))and initial['position']==im['position']and initial['version']==im['version']and initial['epoch']==im['epoch'],'image checkpoint semantic binding'
 for slot_index in range(len(z['q'])):
  off=0xb0000+slot_index*1568;rawslot=image[off:off+1568];assert struct.unpack_from('<II',rawslot)==(0x47444331,slot_index),'slot identity'
  assert list(struct.unpack_from('<IIHHI',rawslot,16))==[*map(int,z['decay'][slot_index]),*map(int,z['beta'][slot_index]),0],'gate image binding'
  for j,key in enumerate(('q','k','v')):assert np.array_equal(np.frombuffer(rawslot[32+j*512:32+(j+1)*512],dtype='<i2').reshape(2,128),z[key][slot_index]),'coefficient image binding'
 rows=[json.loads(x)for x in(a.run/'actual.jsonl').read_text().splitlines()];raw=(a.run/'actual.bin').read_bytes();stage_data=(a.run/'stages.bin').read_bytes();assert len(raw)==len(rows)*SNAP and len(stage_data)%40==0
 stage_rows={};stage_count=0
 for off in range(0,len(stage_data),40):
  record,*rest=struct.unpack_from('<6I2q',stage_data,off);assert record<len(rows),'stage command';stage_rows.setdefault(record,[]).append(tuple(rest));stage_count+=1
 state=z['state_initial'].copy();y=z.get('initial_output',np.zeros((2,128),dtype=np.int64));units=list(map(int,z['state_units']));vu=list(map(int,z['value_units']));ep=im['epoch'];pos=im['position'];ver=im['version'];bank=im.get('bank',0);commits=0;totals={k:0 for k in('cycles','reads','writes','s_reads','s_writes','beats','transactions','mul','wide_calls','alpha_bypass')};retry_count=0;checked_stages=0;status_counts={}
 for index,row in enumerate(rows):
  assert set(row)==ROW and row['schema']=='gdn104-row-v1'and row['index']==index,'row schema/index'
  for k in ROW-{'schema','label','abort_injected'}:assert type(row[k])is int and row[k]>=0,(k,'integer type')
  assert type(row['label'])is str and type(row['abort_injected'])is bool
  assert row['op']in(0,1)and row['bank']in(0,1)and row['state_validated']in(0,1)and row['units_raw']<65536 and row['epoch']<1<<32 and row['generation']<1<<32 and row['position']<1<<64 and row['version']<1<<64,'row ranges'
  assert row['transactions']==row['reads']+row['writes']and row['beats']==row['transactions']*5,'physical link contract'
  assert row['status']in(0,2,3,4,6,7,8,9,10,11,12),'status'
  status_counts[str(row['status'])]=status_counts.get(str(row['status']),0)+1
  slot=row['slot'];committed=row['op']==1 and row['status']==0 or row['label']=='restore-hardcommit'
  fixture_reject=rm['mode']=='fixture'and row['op']==1 and row['status']!=0
  if fixture_reject:
   expected_code=None;attempts=[]
   if pos==(1<<64)-1 or ver==(1<<64)-1:expected_code=4
   else:
    try:step(state,z['q'][slot],z['k'][slot],z['v'][slot],z['decay'][slot],z['beta'][slot],units,vu,ep)
    except Refusal as e:expected_code=e.code;attempts=e.attempts
    except ValueError as e:
     expected_code={'E_STATE':11,'QKV symmetric S16':10,'gates':10,'E_FORMAT shift':12}.get(str(e));assert expected_code is not None,('unknown refusal',str(e))
   assert expected_code==row['status'],('independent refusal',expected_code,row['status'])
   actual=stage_rows.get(index,[]);assert actual==list(observations(attempts)),('refusal stage mismatch',index);checked_stages+=len(actual)
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
  elif not fixture_reject:assert not stage_rows.get(index),('unexpected stages',index)
  sn=snapshot(raw[index*SNAP:(index+1)*SNAP]);assert np.array_equal(sn['state'],state)and np.array_equal(sn['y'],y),(index,'independent numerical mismatch')
  for k,v in [('units',units),('value_units',vu),('epoch',ep),('position',pos),('version',ver),('bank',bank)]:assert sn[k]==v,(index,k,sn[k],v)
  assert(row['position'],row['version'],row['epoch'],row['units_raw'],row['bank'])==(pos,ver,ep,(units[0]&255)|((units[1]&255)<<8),bank),'DUT published metadata'
  if row['op']==1 and row['status']==0:assert row['retries']==len(attempts)-1 and row['offer_hold']>=8 and row['state_validated']==1,'commit protocol'
  for k in totals:totals[k]+=row[k]
 if rm['mode']=='fixture':assert len(rows)==2 and rows[0]['status']==0 and rows[1]['status']==im['expected_status'],'fixture coverage'
 if rm['mode']=='checkpoint':assert commits==1 and len(rows)==2 and [x['op']for x in rows]==[0,1]and all(x['status']==0 for x in rows),'complete checkpoint'
 if rm['mode']=='real':assert commits==rm['steps']==im['steps']and all(x['status']==0 for x in rows),'complete profile'
 if rm['mode']=='protocol':
  phases=[20,23,30,40,50,9,10,60,80,90,102,104,1000,1002];labels=['restore','peer-held-reject','peer-held-restore','restore-stale']+sum(([f'abort{x}',f'restore-abort{x}']for x in phases),[])+['restore-hardprivate','restore-hardcommit','commit-drain']
  assert [r['label']for r in rows]==labels and status_counts.get('2')==14 and status_counts.get('3')==1 and commits==2,'complete recovery labels/count'
  for j,phase in enumerate(phases):assert rows[4+2*j]['status']==2 and rows[4+2*j]['abort_injected']is True and rows[4+2*j]['aborts']==j+1,'actual abort counter'
  assert rows[3]['stale']==1 and rows[1]['status']==3 and rows[1]['offer_hold']>=8,'actual stale/reject'
  events=[json.loads(x)for x in(a.run/'protocol.jsonl').read_text().splitlines()];assert [x['test']for x in events]==['cfg_pending','abort1000','abort1002','hardreset-private','hardreset-commit','commit-drain'],'write/reset coverage'
 receipt={'schema':'gdn104-receipt-v1','status':'PASS_COMPLETE_INTEGER_GATE_NOT_PPA'if rm.get('implementation')=='gate'else'PASS_COMPLETE_INTEGER_RTL_NOT_PPA','contract':CONTRACT,'run_manifest_sha256':sha(a.run/'manifest.json'),'input_manifest_sha256':sha(a.input/'manifest.json'),'receiver_sha256':sha(__file__),'reference_sha256':sha(Path(__file__).with_name('reference.py')),'source':rm['source'],'profile':im['profile'],'mode':rm['mode'],'stall':rm['stall'],'commands':len(rows),'commits':commits,'range_waves':retry_count,'complete_state_cells_checked':len(rows)*32768,'complete_output_codes_checked':len(rows)*256,'stage_pairs_checked':checked_stages,'status_counts':status_counts,'totals':totals,'final':{'position':pos,'version':ver,'units':units,'epoch':ep,'bank':bank},'limits':['standalone GDN; no shared M/A/V integration','no physical macro/PPA','consumer accept external contract; no full gated norm','32 finite coefficient slots; not full256']}
 assert checked_stages==stage_count
 (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf8',newline='\n');print(json.dumps(receipt))
if __name__=='__main__':main()
