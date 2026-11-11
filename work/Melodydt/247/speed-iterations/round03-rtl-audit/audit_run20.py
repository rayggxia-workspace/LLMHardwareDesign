"""Read-only run20 raw evidence audit; stdlib only, never invokes EDA."""
import bisect
import hashlib
import itertools
import json
from pathlib import Path
import re
import tarfile

ROOT=Path('D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/247')
RECEIPTS=ROOT/'run20/receipts'
OUT=Path(__file__).resolve().parent
EXPECTED='87842b59e42fb0773eedb82dce4981614432868fa12218c3aa15166b0b839eff'
ALWAYS={0,1,2,4,5,7,8,14,15,16,20,23,24,25,26}
VENDOR=re.compile(r'^\s*(\d+) (Reading|Writing) .*\.banks\[([0-3])\]\.memory addr0=([01]+) (?:din0|dout0)=([01]+)\s*$')

def require(ok,why):
 if not ok:raise ValueError(why)

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def manifest(path):return {n:d for d,n in (s.split('  ',1) for s in Path(path).read_text().splitlines())}
def numeric_rows(text,prefix):
 return [{k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',s)} for s in text if s.startswith(prefix+' ')]

def read_vectors(path):
 """Recompute expectations from the actual serialized16KiB images, no RTL import."""
 cases=[];prefix_checks=0;ties=[]
 with Path(path).open() as f:
  count=int(next(f))
  for _ in range(count):
   cid,nc,nw,nb,rd,ad,hold,qual=map(int,next(f).split());image={}
   for _ in range(nw):
    a,v=next(f).split();image[int(a)]=int(v,16)
   cmds=[];sums={};read_lines=0
   for _ in range(nc):
    z=next(f).split();require(len(z)==17,'vector command width')
    values=list(map(int,z[:14]));sat,out,raw=map(lambda v:int(v,16),z[14:]);cmd=dict(zip(('ctx','tag','ki','total','k','n','shift','first','last','a','b','out','error','next'),values))
    cmd.update(saturation=sat,value=out,raw=raw)
    if not cmd['error']:
     def byte(addr):return (image[addr//16]>>(8*(addr%16)))&255
     a=[]
     for k in range(cmd['k']):
      v=sum(byte(cmd['a']+4*k+j)<<(8*j) for j in range(4));a.append(v-(1<<32) if v>>31 else v)
     accum=[0]*cmd['n'] if cmd['first'] else sums[cmd['ctx']][:]
     for n in range(cmd['n']):
      for k in range(cmd['k']):
       v=byte(cmd['b']+k*cmd['n']+n);v=v-256 if v&128 else v
       accum[n]+=a[k]*v
     sums[cmd['ctx']]=accum
     require(all(-(1<<95)<=v<(1<<95) for v in accum),'oracle S96 bound')
     packed=sum((v&((1<<96)-1))<<(96*i) for i,v in enumerate(accum));require(packed==raw,'serialized S96 prefix')
     expect=0;saturation=0
     for n,v in enumerate(accum):
      unit=1<<cmd['shift'];q,rem=divmod(v,unit)
      if cmd['shift'] and (2*rem>unit or (2*rem==unit and q%2)):q+=1
      saturation|=int(q<-(1<<31) or q>(1<<31)-1)<<n
      q=max(-(1<<31),min((1<<31)-1,q));expect|=(q&0xffffffff)<<(32*n)
     require(cmd['next']==cmd['ki']+cmd['k'],'oracle next K')
     require(out==(expect if cmd['last'] else 0) and sat==(saturation if cmd['last'] else 0),'serialized RNE/S32')
     read_lines+=1+(cmd['b']%64+cmd['k']*cmd['n']+63)//64;prefix_checks+=1
     if cmd['k']==1 and cmd['shift']==1 and abs(a[0]) in (1,3,5,7) and not sat:ties.append(a[0])
    else:require(not out and not sat and not raw,'invalid vector payload')
    cmds.append(cmd)
   backs={}
   for _ in range(nb):
    a,v=next(f).split();backs[int(a)]=int(v,16)
   for c in cmds:
    if not c['error'] and c['last']:
     require(backs[c['out']//16]==c['value']&((1<<128)-1) and backs[c['out']//16+1]==c['value']>>128,'oracle S outputs')
   cases.append(dict(case=cid,commands=cmds,image=image,backs=backs,read_lines=read_lines,
                     write_words=2*sum(not c['error'] and c['last'] for c in cmds),read_delay=rd,ack_delay=ad,done_hold=hold,qualified=bool(qual)))
  require(not f.read().strip(),'unparsed vector tail')
 require(sorted(set(ties))==[-7,-5,-3,-1,1,3,5,7],'non-saturating signed tie coverage')
 return cases,prefix_checks

def audit_run(row,cases):
 folder=RECEIPTS/'results'/Path(row['log']).parent;measurements=row['case_measurements'];byid={q['case']:q for q in measurements}
 firsts=[byid[i]['first_accept'] for i in range(len(cases))];lasts=[byid[i]['last_done'] for i in range(len(cases))]
 per=[dict(accepted=0,done=0,leaf=0,commit=0,reads=[],writes=[],read_acks=[],write_acks=[],rq=[],wq=[],peak=[0,0,0]) for _ in cases]
 valid_cases=[[cmd for cmd in c['commands'] if not cmd['error']] for c in cases]
 physical={};fields_checked=0;count=0;reset_commands=[];reset_rows=[]
 paths=[folder/n for n in ('control.txt','inputs.txt','actual.txt','probe.log','probe-control.txt')]
 with paths[0].open() as fr,paths[1].open() as fi,paths[2].open() as fa,paths[3].open() as fp,paths[4].open() as fc:
  for raw in fr:
   values=list(map(int,raw.split()));require(len(values)==47,'raw control width');iv=values[:20];av=values[20:]
   il,al,pl,cl=fi.readline(),fa.readline(),fp.readline(),fc.readline()
   require(list(map(int,il.split()))==iv,'raw -> inputs projection')
   require(al.startswith('CONTROL ') and list(map(int,al.split()[1:]))==av,'raw -> actual projection')
   require(pl.startswith('CONTROL ') and pl==cl,'raw probe -> probe-control projection')
   pv=list(map(int,pl.split()[1:]));require(len(pv)==27 and iv[0]==av[0]==pv[0]==count,'continuous globalcycle')
   if count:
    selected=set(ALWAYS)
    if av[2]:selected.add(3)
    if av[5]:selected.add(6)
    if av[8]:selected.update(range(9,14))
    if av[14]:selected.update(range(17,20))
    if av[20]:selected.update((21,22))
    for field in selected:require(av[field]==pv[field],f'raw control/probe mismatch cycle{count} field{field}')
    fields_checked+=len(selected)
   else:require(iv[1]==1,'first reset')
   require(av[24]<=8 and av[25]<=2 and av[26]<=row['BUFFERS'] or count==0,'finite bounds in raw cycles')
   if iv[1]:reset_rows.append((count,iv,av))
   if not iv[1] and iv[2] and av[1] and iv[4]==0xdead:reset_commands.append(count)
   index=bisect.bisect_right(firsts,count)-1
   if index>=0 and count<=lasts[index]:
    c=cases[index];state=per[index];cmds=c['commands'];require(not iv[1],'reset inside completed case')
    state['peak']=[max(state['peak'][i],av[26-i]) for i in range(3)]
    if iv[2] and av[1]:
     cmd=cmds[state['accepted']];require(iv[3:15]==[cmd[k] for k in ('ctx','tag','ki','total','k','n','shift','first','last','a','b','out')],'accepted actual descriptor differs')
     state['accepted']+=1
    if iv[16] and av[4]:
     require(state['rq'],'unmatched read response');origin=state['rq'].pop(0);state['read_acks'].append(count-origin)
    if iv[18] and av[7]:
     require(state['wq'],'unmatched write response');origin=state['wq'].pop(0);state['write_acks'].append(count-origin)
    if av[2] and iv[15]:
     state['reads'].append((count,av[3]));state['rq'].append(count)
     for bank in range(4):physical[count,bank]=('Reading',av[3],c['image'][av[3]*4+bank])
    if av[5] and iv[17]:
     state['writes'].append((count,av[6]));state['wq'].append(count)
     require(av[6] in c['backs'],'unqualified physical write destination')
     physical[count,av[6]%4]=('Writing',av[6]//4,c['backs'][av[6]])
    valid=valid_cases[index]
    if av[16]:
     cmd=valid[state['leaf']];require((av[17],av[18],av[19])==(cmd['ctx'],cmd['next'],state['leaf']),'actual leaf order/K');state['leaf']+=1
    if av[20]:
     cmd=valid[state['commit']];require((av[21],av[22])==(cmd['ctx'],cmd['next']),'actual commit ctx/K');state['commit']+=1
    if av[8] and iv[19]:
     cmd=cmds[state['done']];require(av[9:14]==[cmd[k] for k in ('ctx','tag','next','last','error')],'actual ordered response fields');state['done']+=1
   count+=1
  require(not fi.read() and not fa.read() and not fc.read(),'derived control file tail')
  require(fp.readline().strip()==f'FINITE_CONTROL_REPLAY_PASS cycles={count}' and not fp.read().strip(),'raw probe completion')
 require(count==row['control']['cycles'] and fields_checked==row['control']['compared_fields'],'replay counters differ')
 nominal_r=set();nominal_w=set();qualified=[]
 for i,c in enumerate(cases):
  s=per[i];q=byid[i];valid=sum(not d['error'] for d in c['commands'])
  require((s['accepted'],s['done'],s['leaf'],s['commit'],len(s['reads']),len(s['writes']),len(s['read_acks']),len(s['write_acks']))==
          (len(c['commands']),len(c['commands']),valid,valid,c['read_lines'],c['write_words'],c['read_lines'],c['write_words']),'raw control work conservation')
  require(not s['rq'] and not s['wq'],'outstanding S responses at done')
  require(s['peak']==[q['peak_buffers'],q['peak_reads'],q['peak_reservations']],'raw resource peaks')
  if q['label']=='completion_credit8':require(s['peak'][2]==8,'eight reservations not exercised')
  if c['qualified']:
   require(not(c['read_delay'] or c['ack_delay'] or c['done_hold']),'artificial delay in headline')
   nominal_r.update(s['read_acks']);nominal_w.update(s['write_acks'])
   qualified.append({k:q[k] for k in ('label','commands','accepted_to_done_cycles','accepted_to_next_ready_cycles','peak_buffers','peak_reads','peak_reservations')})
 require(nominal_r==nominal_w=={2},'nominal ACK latency is not2')
 require(len(reset_commands)==20,'actual reset command count')
 # Extract the raw post-reset edges for every deliberate reset command. The
 # actual RTL kept issuing no requests/completions for20 cycles afterwards.
 reset_start=[]
 phase='idle';remaining=0;accepted=None;command_index=0
 with paths[0].open() as f:
  for line in f:
   v=list(map(int,line.split()));cycle=v[0]
   if command_index<len(reset_commands) and cycle==reset_commands[command_index]:
    require(phase=='idle','overlapping reset observation');accepted=cycle;phase='waiting';command_index+=1
   elif phase=='waiting' and v[1]:reset_start.append(cycle-accepted);phase='reset'
   elif phase=='reset' and not v[1]:phase='observe';remaining=20
   if phase=='observe':
    require(not any((v[22],v[25],v[28],v[44],v[45],v[46])),'post-reset ghost S request/completion/reservation')
    remaining-=1
    if remaining==0:phase='idle'
 require(command_index==20 and phase=='idle','short reset observation')
 require(reset_start==list(range(1,21)),'reset stage coverage differs')
 # Reconstruct actual vendor-memory words, and match every service operation
 # back to control acceptance and the independent initialization/output oracle.
 memory={};seen=set();vendor_count=0;memory_reads=0;physical_words=0;out_words=0;control_markers=[];proof=[];last_tick=-1;tick_banks=set()
 with (RECEIPTS/'results'/row['log']).open() as f:
  for line in f:
   require('%Error' not in line and 'Assertion failed' not in line,'actual RTL failure marker')
   m=VENDOR.match(line)
   if m:
    t=int(m[1]);kind=m[2];bank=int(m[3]);address=int(m[4],2);value=int(m[5],2)
    require(t%10==6,'unexpected SRAM timestamp phase');tick=(t-6)//10
    if tick!=last_tick:last_tick=tick;tick_banks=set()
    require(bank not in tick_banks,'same bank performed two physical operations/edge');tick_banks.add(bank);require(len(tick_banks)<=4,'free extra SRAM banks')
    key=(bank,address)
    if kind=='Writing':memory[key]=value
    else:require(key in memory and memory[key]==value,'vendor SRAM response differs from actual previous write');memory_reads+=1
    if (tick,bank) in physical:
     require((kind,address,value)==physical[tick,bank],'actual SRAM operand/result word differs from oracle/control');seen.add((tick,bank));physical_words+=1;out_words+=kind=='Writing'
    vendor_count+=1
   elif line.startswith('R3_CASE '):control_markers+=numeric_rows([line],'R3_CASE')
   elif line.startswith('R3_PASS '):proof+=numeric_rows([line],'R3_PASS')
 require(seen==set(physical),'missing actual physical SRAM operations')
 require(len(control_markers)==66 and proof==[row['checks']],'raw RTL summary markers differ')
 for marker in control_markers:
  q=byid[marker['case']];require(all(q.get(k)==v for k,v in marker.items()),'raw case summary mismatch')
 return dict(BUFFERS=row['BUFFERS'],mode=row['mode'],seed=row['seed'],raw_cycles=count,control_fields_compared=fields_checked,
  valid_packets=7458,actual_scalar_S96_assertions=7458*8,final_S_words_checked=out_words,physical_service_words_checked=physical_words,
  vendor_memory_operations=vendor_count,vendor_memory_reads_checked=memory_reads,nominal_read_ACK=[2],nominal_write_ACK=[2],
  reset_offsets=reset_start,qualified=qualified,
  content_reviewed=[p.relative_to(RECEIPTS).as_posix() for p in paths]+['results/'+row['log']])

def main():
 result_path=RECEIPTS/'results/result.json';require(sha(result_path)==EXPECTED,'result SHA identity')
 r=json.loads(result_path.read_bytes());m=json.loads((RECEIPTS/'inputs.json').read_bytes());c=json.loads((RECEIPTS/'collection.json').read_bytes())
 require(r['passed'] is True and not any(r.get(k) for k in ('error','errors','traceback')),'main failure flags')
 require(r['source_commit']==m['source_commit']==c['source_commit'],'commit identity')
 require(r['manifest_sha256']==sha(RECEIPTS/'inputs.json')==c['input_manifest_sha256'],'input manifest binding')
 require(c['job']['state']=='COMPLETED' and c['job']['exit_code']=='0:0' and c['whole_run_passed'] and not c['warnings'],'terminal job classification')
 accounting=(RECEIPTS/'sacct.txt').read_text().strip().split('|')
 require(accounting==[c['job'][k] for k in ('job_id','job_name','state','exit_code','elapsed','nodes')],'raw sacct differs from collection')
 allocation=(RECEIPTS/'allocation.txt').read_text()
 require('JobId='+c['job']['job_id'] in allocation and 'NumCPUs=4' in allocation and 'Partition=c64' in allocation and 'NodeList=node1' in allocation,'actual Slurm allocation')
 require(all(r['gates'].values()) and not r['physical_qualified'] and not r['full_P_DMA_integration'],'gate/qualification scope')
 hashes=manifest(RECEIPTS/'output-files.sha256');files=[p for p in (RECEIPTS/'results').rglob('*') if p.is_file()]
 for p in files:require(sha(p)==hashes[p.relative_to(RECEIPTS).as_posix()],'actual selected output SHA '+str(p))
 code=manifest(RECEIPTS/'source-files.sha256');require(code==m['code_sha256'],'source manifest binding')
 require([v for k,v in code.items() if k.endswith('/job.sh')]==[sha(RECEIPTS/'job.sh')],'launched job script differs from source')
 frozen={'r3_m_finite.sv':'783089199218a48c3c6cfe78a67509dba1ee95ea23858f7c7e79737e7911510c',
         'm_s32_stream_candidate.sv':'20169790ef33176da607adfcb9f1c5847b457eec6aeaec8800ff212f7cab47d4',
         'tb_r3_m_finite.sv':'8b20de2a7b3f41e9e4a8a49c78d3cd1d52044b9a8809505dff0ab1062c46e86a',
         'vectors.py':'140cf9673051495acf7212dc6b898154b1c7dd994eaaa6d054e09fef3f92f020',
         'finite_control.hpp':'1e8bec30e3ae7b28ca130ddce9bc1f08604ed39c261cf4d05ad37ea3100fc662',
         'control_probe.cpp':'2b03434413ca02bb51bf8bc432143be767fa8bd46553f71c557279e0bcb42d86'}
 for name,digest in frozen.items():require([v for k,v in code.items() if k.endswith('/'+name)]==[digest],'frozen R3 source changed '+name)
 input_lock=manifest(RECEIPTS/'input-files.sha256');require(input_lock==m['input_sha256'],'input lock binding')
 require(sha(RECEIPTS.parent/'payload.tar')==m['payload_sha256'],'payload identity')
 with tarfile.open(RECEIPTS.parent/'payload.tar') as t:
  for path,digest in code.items():require(hashlib.sha256(t.extractfile('source/'+path).read()).hexdigest()==digest,'source snapshot '+path)
  for path,digest in input_lock.items():require(hashlib.sha256(t.extractfile(path).read()).hexdigest()==digest,'input snapshot '+path)
 for path,digest in r['rtl_source_sha256'].items():require(code[path]==digest,'measured source drift')
 for cmd in r['commands']:
  require(cmd['exit_code']==0 and sha(RECEIPTS/'results'/cmd['log'])==cmd['log_sha256'],'command/raw-log identity')
  if '-j' in cmd['command']:require(int(cmd['command'][cmd['command'].index('-j')+1])<=4,'build exceeds actual CPU allocation')
 cases,prefix_checks=read_vectors(RECEIPTS/'results/vectors/vectors.txt')
 require(len(cases)==66 and prefix_checks==7458 and sha(RECEIPTS/'results/vectors/vectors.txt')==r['vectors']['vectors_sha256'],'actual input vector identity')
 require(len(r['runs'])==6 and len(r['profile']['rows'])==24,'actual configuration coverage')
 require({(q['BUFFERS'],q['mode'],q['seed']) for q in r['runs']}=={(b,m,s) for b in (1,2) for m,s in ((1,143),(2,143),(2,144))},'actual configuration identities')
 require(sha(RECEIPTS/'results/vectors/vectors.json')==r['vectors']['metadata_sha256'],'vector metadata identity')
 ledger=r['resource_ledger'];fixed=sum(ledger['wrapper_fixed_bits'].values());per=sum(ledger['wrapper_per_packet_bits'].values());leaf=sum(ledger['original_K16_leaf_bits'].values())
 require(per==2158 and leaf==12912,'area declaration arithmetic')
 for choice in ledger['choices']:
  require(choice['wrapper_register_bits']==fixed+per*choice['BUFFERS'] and choice['leaf_plus_wrapper_register_bits']==fixed+per*choice['BUFFERS']+leaf,'area ledger arithmetic')
 require(ledger['existing_P_S_bytes']==16384 and ledger['existing_S_macros']==4,'SRAM budget drift')
 require(r['profile']['ack_delays']['nominal_read_accept_to_consumed_ack_cycles']==r['profile']['ack_delays']['nominal_write_accept_to_consumed_ack_cycles']==[2],'profile ACK claim')
 runs=[]
 for row in r['runs']:
  require(row['passed'] and row['checks']==dict(buffers=row['BUFFERS'],cases=66,checks=7638,reset_cases=20),'run business markers')
  require(sha(RECEIPTS/'results'/Path(row['log']).parent/'vectors.txt')==r['vectors']['vectors_sha256'],'per-run input image differs')
  runs.append(audit_run(row,cases))
  print('AUDITED',row['BUFFERS'],row['mode'],row['seed'],flush=True)
 timings={}
 for row in runs:
  for q in row['qualified']:
   key=(row['BUFFERS'],q['label']);value=(q['accepted_to_done_cycles'],q['accepted_to_next_ready_cycles'])
   require(key not in timings or timings[key]==value,'qualified timing differs across seeds');timings[key]=value
 profile_keys=set()
 for p in r['profile']['rows']:
  key=(p['BUFFERS'],p['mode'],p['seed']);run=next(q for q in r['runs'] if (q['BUFFERS'],q['mode'],q['seed'])==key)
  q=p['measurement'];require(q in run['case_measurements'] and q['qualified'],'profile does not match actual qualified case')
  require(p['log']==run['log'] and p['log_sha256']==run['log_sha256'] and p['control_sha256']==run['control']['raw_control_sha256'],'profile raw-log/control source binding')
  require(p['events_sha256']==sha(RECEIPTS/'results'/q['events_file']),'profile event file source binding')
  require((*key,q['case']) not in profile_keys,'duplicate profile source');profile_keys.add((*key,q['case']))
 require(len(profile_keys)==24,'profile actual case coverage')
 reviewed={'results/result.json','inputs.json','collection.json','source-files.sha256','input-files.sha256','output-files.sha256','results/vectors/vectors.txt','sacct.txt','allocation.txt','job.sh'}
 for q in runs:reviewed.update(q.pop('content_reviewed'))
 artifact_rows=[dict(path=n,sha256=sha(RECEIPTS/n),bytes=(RECEIPTS/n).stat().st_size) for n in sorted(reviewed)]
 report=dict(passed=True,source_commit=r['source_commit'],job=c['job'],main_result_sha256=EXPECTED,
  scope='Read-only raw evidence audit; no local EDA, no copied raw logs, no physical/full-P/LLM qualification',
  all_selected_outputs_sha_verified=len(files),all_output_manifest_entries=len(hashes),source_members_sha_verified=len(code),
  serialized_numeric_prefixes_recomputed=prefix_checks,actual_prefix_proof='Frozen bench asserted all8 actual S96 accum values after each real commit; raw control has no numeric payload. Raw SRAM inputs and final writes independently checked below.',
  resource_proxy=dict(single_wrapper_bytes=ledger['choices'][0]['wrapper_register_bytes'],double_wrapper_bytes=ledger['choices'][1]['wrapper_register_bytes'],extra_buffer_bits=per,extra_buffer_bytes=per/8,S_bytes=16384),
  frozen_source_sha256=frozen,external_bank=dict(recorded_sha256=r['bank_sha256'],local_rehash=False,scope='Passed server runner locked the external bank SHA; this audit did not reread the server dependency'),
  runs=runs,content_reviewed_files=artifact_rows,
  SHA_only_scope='Every locally collected regular results file was streamed and matched output-files.sha256; uncollected object files were not read, rerun, or rehashed.',
  limitations=['S96 values are not present in raw control; actual S96 assertions are tied to frozen bench/source and successful original logs.',
               'Continuous RTL program cycles are not directly old-SystemC K256 costs; that policy must retain its explicit ticket-drain boundary.',
               'No actual P/DMA/LC integration, 300MHz STA, physical area or full-LLM execution qualification.'])
 (OUT/'audit.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
 lines=['# run20 独立原始证据审计','',f"结论：PASS。源码 `{r['source_commit']}`；Slurm {c['job']['job_id']}，{c['job']['state']} {c['job']['exit_code']}。",'',
  f"主结果SHA `{EXPECTED}`。流式核验{len(files)}个已回收输出与{len(code)}个payload源码成员；未复制327MiB原始材料，未执行EDA。",'',
  '六次实际运行各66例，7458个有效packet、7638项检查和20个reset时点。完整47字段原始控制逐行投影核对并与实际server probe在有效字段上匹配；仅忽略首个reset边沿前未初始化payload。',
  '独立重算serialized S96/RNE oracle；实际输入SRAM字、最终输出字与原始vendor日志逐字核对。S96内部数值未被control记录，其实际逐列断言通过依赖冻结bench和原始PASS证据，不能称control replay验证了数值。','',
  '| 配置 | K2048 ctx1 | K11008 ctx1 | K2048 ctx8 | K11008 ctx8 |','|---|---:|---:|---:|---:|']
 for buf in (1,2):
  row=next(q for q in runs if q['BUFFERS']==buf)
  lines.append('| BUF'+str(buf)+' | '+' | '.join(str(v['accepted_to_done_cycles']) for v in row['qualified'])+' |')
 lines+=['','以上为首cmd接受至最后done消费的连续RTL程序周期，三seed一致；不能直接当旧K256模型费用。无人工hold的读/写请求→消费ACK均严格2拍。正常峰值不超过2个读metadata、8项completion和各自1/2 input buffer，压力例实际填满8票。',
  '原S仍16KiB/4×1RW；额外buffer声明位数2158位=269.75B，wrapper479.5→749.25B。只是源码结构代理，未取得面积或300MHz资格。','',
  '实际内容审阅的文件及原SHA逐项列于audit.json；所有其他已回收results文件仅做流式SHA匹配。未回收object/binary仅有服务器清单，未冒称本地审核。']
 (OUT/'audit.md').write_bytes(('\n'.join(lines)+'\n').encode())
 print('RUN20_INDEPENDENT_AUDIT_PASS',flush=True)

if __name__=='__main__':main()
