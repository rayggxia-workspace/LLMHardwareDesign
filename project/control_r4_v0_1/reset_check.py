"""Observe real reset, loaders, whole control packets and new-cohort DMA data."""
import network_check,run as common,dma_check
need=common.check_cycles.need;codec=common.codec
def check(log,scenario,images):
 tr=network_check.decode(log);r={};configs={};pm={};cfg={};shadow={};prepared=set();starts=[];results=[];contexts={};taskseq={};first_admit={};lastreset=False;final_lines=[];probes=0;terminals={};ready_seen={}
 for line in log.splitlines():
  if line.startswith('R '):
   a=[int(x) for x in line.split()[1:]];t,phase,reset,admit,gen,epoch,seq,acks,mask,mvalid,lvalid,quiet=a
   r[t]=dict(phase=phase,reset=reset,admit=admit,gen=gen,epoch=epoch,seq=seq,acks=acks,mask=mask)
   need(not admit or phase==3 and acks==255 and mask==7,'cohort admitted before all ACKs/full loader witnesses')
  elif line.startswith('P '):
   a=line.split();need(int(a[2])==2 and int(a[4],16)==int.from_bytes(bytes(range(16)),'little')^int.from_bytes((1).to_bytes(4,'little')*4,'little'),'reset did not retain known committed S bytes');probes+=1
 for index,row in enumerate(tr['mother']):
  t=row['cycle'];s=row['signals'];ls=[common.check_cycles.sample(x['cycles'][index]['signals']) for x in tr['locals']]
  if t not in r:continue
  c=r[t];gen=c['gen'];reset=bool(c['reset'])
  if reset and not lastreset:contexts={};taskseq={};pm={};cfg={}
  for b,pins in [(0,ls[0]),(1,ls[1]),(2,s)]:
   if reset:
    if lastreset:need(not pins['image_valid_o'] and not (pins.get('event_valid_o',0) or pins.get('result_valid_o',0)),'old image/result survived synchronous cohort reset')
    continue
   key=(gen,b);data=images['mother' if b==2 else 'local'+str(b)];state=configs.setdefault(key,dict(writes=set(),reads=set()))
   if pins['pm_req_valid_o'] and pins['pm_req_ready_i']:
    need(b not in pm,'reset PM duplicate ownership');addr=pins['pm_req_address_o'];need(addr%16==0,'PM alignment');pm[b]=(pins['pm_req_write_o'],addr,pins['pm_req_data_o'])
   if pins['pm_rsp_valid_i'] and pins['pm_rsp_ready_o']:
    need(b in pm,'reset PM reply without owner');wr,addr,value=pm.pop(b)
    if wr:shadow[b,addr]=value
    else:need(pins['pm_rsp_data_i']==shadow.get((b,addr),int.from_bytes(b'\xcd'*16,'little')),'PM actual read differs from committed write')
   if pins['cfg_req_valid_i'] and pins['cfg_req_ready_o']:
    need(b not in cfg and pins['cfg_req_generation_i']==gen,'loader generation/ownership');op,addr=pins['cfg_req_op_i'],pins['cfg_req_address_i'];cfg[b]=(op,addr)
    if op==1:need(addr<len(data) and pins['cfg_req_data_i']==int.from_bytes(data[addr:addr+16],'little'),'loader write input differs')
   if pins['cfg_rsp_valid_o'] and pins['cfg_rsp_ready_i']:
    need(b in cfg and pins['cfg_rsp_status_o']==0,'loader response failed/unowned');op,addr=cfg.pop(b)
    if op==1:state['writes'].add(addr)
    if op==2:
     need(pins['cfg_rsp_data_o']==int.from_bytes(data[addr:addr+16],'little'),'full readback mismatch');state['reads'].add(addr)
    if op==4:
     need(state['writes']==state['reads']==set(range(0,len(data),16)),'PREPARE before full reload/readback');prepared.add(key)
  if c['admit'] and gen not in first_admit:
   need(all((gen,b) in prepared for b in range(3)),'cohort admitted without actual three-port PREPARE');first_admit[gen]=t
  accepted=[b for b in (0,1) if ls[b]['task_valid_i'] and ls[b]['task_ready_o']]
  taskfire=s['task_valid_o'] and s['task_ready_i'];need(accepted==([s['task_target_o']] if taskfire else []),'reset MC/LC task atomicity')
  if s['start_valid_i'] and s['start_ready_o']:
   need(c['admit'] and s['start_epoch_i']==c['epoch'] and s['start_generation_i']==gen,'START outside new generation/epoch gate');starts.append((gen,s['start_job_i']))
  if taskfire:
   b=accepted[0];need(ls[b]['task_packet_i']==s['task_packet_o'],'reset whole task changed');m=codec.unpack_record('task_message',s['task_packet_o'].to_bytes(64,'little'))
   need(m['kind']==0 and m['epoch']==c['epoch'] and m['job_id']==s['start_job_i'],'stale task identity after reset')
   need(m['task_sequence']==taskseq.get(b,0)+1,'task sequence not reset or not monotonic inside cohort');taskseq[b]=m['task_sequence'];contexts[b]=m
   if b==0:need(ready_seen.get((gen,m['job_id']),t)<t,'producer CALL before actual consumer READY')
  returned=[b for b in (0,1) if ls[b]['event_valid_o'] and ls[b]['event_ready_i']];rfire=s['return_valid_i'] and s['return_ready_o'];need(len(returned)==int(bool(rfire)),'reset return acceptance atomicity')
  if rfire:
   b=returned[0];need(ls[b]['event_packet_o']==s['return_packet_i'],'reset whole return changed');m=codec.unpack_record('event_message',s['return_packet_i'].to_bytes(64,'little'))
   need(b in contexts and all(m[k]==contexts[b][k] for k in ['job_id','epoch','task_sequence']),'old return escaped into new cohort')
   key=(gen,m['job_id'],b)
   if m['kind']==0:
    need(b==1 and (gen,m['job_id']) not in ready_seen,'duplicate/unowned READY');ready_seen[gen,m['job_id']]=t
   else:
    need(m['kind']==2 and m['status']==0 and key not in terminals,'reset duplicated or failed terminal')
    facts=[(time,e['service']) for time,events in tr['events'][b].items() for e in events if e['kind']==3 and e['job']==m['job_id'] and e['epoch']==m['epoch'] and e['task']==m['task_sequence']]
    need(sorted(service for time,service in facts)==([1,2] if b==0 else [1]) and all(time<t for time,service in facts),'terminal before actual service ACKs')
    terminals[key]=t
  if s['result_valid_o'] and s['result_ready_i']:
   need(c['admit'] and s['result_epoch_o']==c['epoch'] and s['result_status_o']==0,'stale/failed global result accepted');results.append((gen,s['result_job_o']))
   need(all(terminals.get((gen,s['result_job_o'],b),t)<t for b in (0,1)) and s['trace_live_tokens_o']==0 and s['trace_block_active_o']==0,'global result before child terminals/credit release')
  lastreset=reset
 need(starts==[(1,7),(2,8),(2,9)],'cohort START sequence')
 need(results==([(1,7)] if scenario in (0,3) else [])+[(2,8),(2,9)],'reset fabricated old result/lost new jobs')
 need(set(first_admit)=={1,2} and (probes==1)==(scenario in (0,1,3,5)),'cohort/probe coverage')
 # Last generation must drain all actual DMA/S/CDC obligations and use fresh data.
 generation=1
 for line in log.splitlines():
  if line.startswith('R '):generation=int(line.split()[5])
  if generation==2:final_lines.append(line)
 dma=dma_check.check('\n'.join(final_lines))
 return dict(starts=starts,results=results,full_reload_ports=len(prepared),payload_retention_probes=probes,new_cohort_DMA=dma,cycles=len(tr['mother']))
def mutations(log,scenario,images):
 out=[]
 for name in ['missing_reset_ACK','partial_reload_admission','old_epoch_START','old_global_result']:
  rows=log.splitlines();changed=False
  if name in ('missing_reset_ACK','partial_reload_admission'):
   for i,line in enumerate(rows):
    if line.startswith('R '):
     a=line.split()
     if a[4]=='1' and a[5]=='2':a[8]='127' if name=='missing_reset_ACK' else a[8];a[9]='3' if name=='partial_reload_admission' else a[9];rows[i]=' '.join(a);changed=True;break
  else:
   # Mutate a real sampled atomic host bundle then re-encode the complete pins.
   import mc_check
   parsed=mc_check.decode(log);pin=next(p for p in mc_check.PINS if p['name']==('start_epoch_i' if name=='old_epoch_START' else 'result_epoch_o'))
   for row in parsed:
    s=row['signals'];fire=s['start_valid_i'] and s['start_ready_o'] if name=='old_epoch_START' else s['result_valid_o'] and s['result_ready_i']
    if fire and s[pin['name']]==2:
     s[pin['name']]=1;value=0
     for p in mc_check.PINS:value=(value<<p['width'])|s[p['name']]
     for i,line in enumerate(rows):
      if line.startswith('C '+str(row['cycle'])+' '):rows[i]='C '+str(row['cycle'])+' '+format(value,'x');changed=True;break
     break
  need(changed,'reset mutation not exercised')
  try:check('\n'.join(rows),scenario,images)
  except (ValueError,KeyError):out.append(dict(name=name,rejected=True));continue
  raise ValueError('accepted reset mutant '+name)
 return out
