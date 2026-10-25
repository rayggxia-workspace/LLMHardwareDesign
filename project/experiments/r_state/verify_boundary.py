"""Receiver-only boundary and fabric event definitions; no RTL oracle imports."""
import json,struct
from reference import step,Guard

def check(v,msg):
 if not v:raise ValueError(msg)
def descriptor(unit,epoch,position,bank=0):return(0x52393901|(position<<32)|(epoch<<64)|((unit&65535)<<96)|(bank<<112)|(1<<118)|(1<<119)).to_bytes(16,'little')
def receive_boundary(run,inp,rm,im):
 from verify import FIELDS
 rows=[json.loads(x)for x in(run/'actual.jsonl').read_text().splitlines()];raw=(run/'actual.bin').read_bytes();check(len(raw)==len(rows)*131600,'boundary complete snapshots');cases={x['name']:x for x in im['synthetic_fixtures']};seen=[];state=None;current=None;results=[];counts={'accepted':0,'rejected':0,'aborted':0};total={k:0 for k in ['cycles','reads','writes','s_reads','s_writes','mul','transactions','beats','alpha_bypass']}
 for i,row in enumerate(rows):
  check(set(row)==FIELDS and row['schema']=='r99-row-v1'and row['index']==i,'boundary exact schema')
  for k,v in row.items():
   if k not in {'schema','label','abort_injected'}:check(type(v)is int,'boundary typed integers')
  check(type(row['abort_injected'])is bool,'boundary bool');check(row['beats']==row['transactions']*5 and row['transactions']==row['reads']+row['writes'],'boundary link inventory')
  name,action=row['label'].split('/');f=cases[name]
  if name!=current:
   check(action=='restore'and name not in seen,'fixture order');seen.append(name);current=name;image=(inp/f['path']).read_bytes();state=list(struct.unpack_from('<32768i',image));y=list(struct.unpack_from('<128i',image,0xa0000));desc=image[0xa0400:0xa0410];unit=f['initial_unit'];epoch=f['initial_epoch'];position=f['initial_position'];bank=0;aborts=0
  expected_status=0;expected_retry=0
  if action in ['restore','restore-again']:
   valid=name not in ['position_overflow','invalid_owner','invalid_profile','invalid_unit'];expected_status=0 if valid else 9;check(row['op']==2 and row['reads']==1 and row['writes']==0,'boundary restore traffic')
  elif action=='abort-reencode':expected_status=2;aborts+=1;counts['aborted']+=1;check(row['abort_injected'],'actual abort injection')
  elif action=='step':
   check(row['op']==1,'boundary STEP');magic,pos,head,res,dt,alpha,skip,res1=struct.unpack_from('<IIIIiIiI',image,0xb0000);v=struct.unpack_from('<640i',image,0xb0020)
   if position>=72 or magic!=0x52393943 or pos!=position or head!=0 or res or res1 or alpha>1<<31:expected_status=4
   else:
    try:
     new,ny,nu,ne,nr=step(state,unit,epoch,v[:128],v[128:384],v[384:],dt,alpha,skip)
     state,y,unit,epoch=new,ny,nu,ne;position+=1;bank^=1;expected_retry=nr;desc=descriptor(unit,epoch,position,bank)
    except Guard as e:
     code=str(e);expected_status={'retry_limit':5,'unit_limit':6,'epoch_limit':7}.get(code,8);expected_retry=8 if code=='retry_limit'else 0
   counts['accepted'if expected_status==0 else'rejected']+=1;results.append({'name':name,'status':expected_status,'retries':expected_retry,'unit':unit,'epoch':epoch,'alpha_bypass':row['alpha_bypass']})
  else:raise ValueError('boundary action')
  check(row['status']==expected_status and row['retries']==expected_retry,'boundary status/retries '+name);check(row['aborts']==aborts and row['stale']==0,'boundary measured protocol counters')
  b=raw[i*131600:(i+1)*131600];check(b[:16]==desc,'published descriptor unchanged or valid atomic switch '+name);check(list(struct.unpack_from('<32768i',b,16))==state,'complete boundary state '+name);check(list(struct.unpack_from('<128i',b,131088))==y,'complete boundary output '+name)
  if expected_status==9:check((row['position'],row['unit'],row['epoch'],row['bank'])==(0,0,0,0),'invalid restore cannot publish mirror')
  else:check((row['position'],row['unit'],row['epoch'],row['bank'])==(position,unit,epoch,bank),'boundary mirror')
  if name=='alpha_one'and action=='step':check(row['alpha_bypass']==32768,'unsigned alpha1 explicit lowering')
  for k in total:total[k]+=row[k]
 check(len(seen)==19 and set(seen)==set(cases),'all fixed boundary fixtures');check(len(rows)==36,'boundary complete command count')
 return {'schema':'r99-receipt-v1','status':'PASS_FULL_HEAD_RTL_BOUNDARIES','mode':'boundary','rows':len(rows),'fixtures':results,'counts':counts,'totals':total,'all_state_codes_compared':len(rows)*32768,'all_readout_codes_compared':len(rows)*128,'external_payload_bytes':total['transactions']*16,'external_wire_bytes':total['transactions']*80}
def receive_protocol(run,rows):
 events=[json.loads(x)for x in(run/'protocol.jsonl').read_text().splitlines()];d={x['test']:x for x in events};check(len(d)==len(events)==8,'protocol event coverage')
 check(d['cfg_pending']=={'test':'cfg_pending','held_cycles':9},'cfg pending actual test');check(d['stale_response']=={'test':'stale_response','injected':1,'observed':1},'actual stale tag')
 for name in ['abort1000','abort1002','commit-drain']:check(d[name]=={'test':name,'write_applied_before_ack':True,'abort_was_accepted':name!='commit-drain'},'late write/commit test')
 for name,pos in [('hardreset-private',0),('hardreset-commit',1)]:
  e=d[name];check(set(e)=={'test','applied_address','cycles','reads','writes','generation','descriptor_position_after_apply','write_ack_not_delivered','fabric_barrier_drained'},'reset event schema');check(e['write_ack_not_delivered']is True and e['fabric_barrier_drained']is True and e['descriptor_position_after_apply']==pos,'reset actual descriptor');check(e['cycles']>0 and e['reads']>0 and e['writes']>0,'partial reset cost')
 check(d['generation_terminal_RTL_register_injection']=={'test':'generation_terminal_RTL_register_injection','injected':4294967294,'observed':4294967295,'rejected_cycles':11,'terminal_stale_drained':1},'terminal generation')
 aborts=0;stale=0
 for row in rows:
  if row['label'].startswith('restore-hard'):aborts=0;stale=0
  if row['label']=='restore-stale':stale=1
  if row['abort_injected']:aborts+=1
  check(row['aborts']==aborts and row['stale']==stale,'actual hardware abort/stale counts')
 check(sum(x['status']==2 for x in rows)==11,'11 phases actual softabort');check(rows[-1]['generation']==0xffffffff,'actual generation terminal')
 return {'events':len(events),'soft_abort_commands':11,'hard_reset_applied_write_cases':2,'generation_terminal_scope':'RTL register injection, not gate-level proof','reset_partial_costs':[d['hardreset-private'],d['hardreset-commit']]}
