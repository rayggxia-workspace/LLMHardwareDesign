"""Independent read-only run22 audit. Stdlib only; never invokes EDA.

Original logs are hashed and parsed in place, never copied. Native op12
results are independently recomputed using the frozen integer LUT contract.
Persistent-state/reset/held-response assertions are bound to frozen sources
and actual PASS, not claimed to be reconstructed from absent reset waveforms.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

SOURCE='7048c35ed2912e80e62bd7827deaec480d4a7e1a'
PAYLOAD='bef21863b43f329e9adf18be7e7a52b096f02a4700d01ff2c94231d1a3cb999d'
ARCHIVE='5105067aeabe69441592d24f491a43f3d3ec7602ba8870678830b40a7b8a3221'
BANK='6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
PRIOR='fb0b4d0d1251140655feea5bd671c196e5ae13b1fd47066dc22d6e1e1a2eac78'
OBSERVED='cc5e13093dd5269e8fcd473e56a524e7a3b4e21d426e064b48ed0fab1f080296'
SEEDS={(1,143),(2,143),(2,144)}
NATIVE_SHA='6efe29ed1121085d59bf072e2c3a062c9c18d67fa0f69a30da16f3b2b56f03ec'
U_SHA='f5e30680ab32cc0a96e25e60268549265fac92373966a449e447cf28df33b413'
LABELS=('baseline_legacy','default_legacy','lanes4_legacy','baseline_batch','disabled_batch','direct_batch',
 'baseline_compute','default_compute','baseline_disabled_compute','disabled_compute','compute',
 'baseline_full_U','default_full_U','baseline_disabled_full_U','disabled_full_U','full_U',
 'baseline_stateless','default_stateless','stateless','group_gate','illegal_lanes')
GATES=('compute_s32','full_U','numeric','lifecycle','default_compatibility','enabled_ordinary',
 'stateless_context_preservation','old_batch_compatibility','default_lanes2_compatibility','direct0_lanes4_compatibility','op12_lanes4_execution')
OLD_LABEL=dict(baseline_legacy='default',default_legacy='default',lanes4_legacy='default',
 baseline_batch='disabled_batch',disabled_batch='disabled_batch',baseline_compute='compute',default_compute='compute',
 baseline_disabled_compute='disabled_compute',disabled_compute='disabled_compute',baseline_full_U='full_U',default_full_U='full_U',
 baseline_disabled_full_U='disabled_full_U',disabled_full_U='disabled_full_U',baseline_stateless='stateless',default_stateless='stateless')
MATCHES=dict(default_legacy='baseline_legacy',lanes4_legacy='baseline_legacy',disabled_batch='baseline_batch',
 default_compute='baseline_compute',disabled_compute='baseline_disabled_compute',default_full_U='baseline_full_U',
 disabled_full_U='baseline_disabled_full_U',default_stateless='baseline_stateless')
CMD=re.compile(r'^R4_TRACE CMD c=(\d+) op=(\d+) count=(\d+) param=([0-9a-fA-F]+) data=([0-9a-fA-F]+) aux=([0-9a-fA-F]+)$')
RSP=re.compile(r'^R4_TRACE RSP c=(\d+) data=([0-9a-fA-F]+) error=(\d+) sat=(\d+)$')
VENDOR=re.compile(r'^\s*(\d+) (Reading|Writing) .*\.banks\[([0-3])\]\.memory addr0=([01]+) (?:din0|dout0)=([01]+)\s*$')

def require(ok,why):
 if not ok:raise ValueError(why)

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def hashes(path):return {n:d for d,n in (s.split('  ',1) for s in Path(path).read_text().splitlines())}
def numbers(line):return {k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}

def is_observed(s):
 return bool(re.match(r'^\s*\d+ (Reading|Writing) ',s) or s.startswith(('COMPAT ','NEXP_COMPUTE ',
  'NEXP_COMPUTE_PASS ','NEXP_FULL_U ','NEXP_U_PASS ','NEXP_NATIVE_PATH ','STATELESS_PASS ')))

def ordinary(rows):
 pending=None;result=[]
 for s in rows:
  m=re.fullmatch(r'COMPAT CMD c=(\d+) lane=1 meta=([0-9a-fA-F]+) (.*)',s)
  if m:
   require(pending is None,'ordinary command overlap');pending=(int(m[1]),int(m[2],16),m[2]+' '+m[3]);continue
  m=re.fullmatch(r'COMPAT DONE c=(\d+) lane=1 (.*)',s)
  if m:
   require(pending is not None,'ordinary response without command');start,meta,data=pending;pending=None
   if meta&15!=15:result.append((data,int(m[1])-start,m[2]))
 require(pending is None,'ordinary unfinished');return result

def exponential(x,lut):
 if x< -16384:return 0
 if x>=0:return 32768
 off=x+16384;index=off//16;delta=(lut[index+1]-lut[index])*(off%16)
 # This is the existing integer RTL interpolation contract, including its
 # quotient-bit tie test; no floating exp or new quantization is substituted.
 return lut[index]+delta//16+int(delta%16>8 or (delta%16==8 and (delta//16)&1))

def parse_log(path,lut,direct,lanes,kind):
 events=[];old=[];markers={};pending=None;native_commands=[];pairs=[];aborted=[];domain=set();numeric=0
 memory={};vendor_reads=vendor_writes=0;last_bank_event=set();last_vendor_time=None
 with Path(path).open(encoding='utf8') as f:
  for raw in f:
   s=raw.rstrip('\r\n')
   require('%Error' not in s and 'FAIL' not in s,'unexpected RTL failure '+str(path))
   if is_observed(s):old.append(s);events.append(s)
   elif s.startswith('R4_TRACE '):events.append(s)
   m=CMD.fullmatch(s)
   if m:
    cmd=dict(cycle=int(m[1]),op=int(m[2]),count=int(m[3]),param=int(m[4],16),data=int(m[5],16),aux=int(m[6],16))
    if pending is not None:
     require((direct==0 and kind in ('compute','full_U')) or pending['op']==12,'only fixed reset sequence may cancel a native response');aborted.append(pending)
    pending=cmd;native_commands.append(cmd)
   m=RSP.fullmatch(s)
   if m:
    require(pending is not None,'native response without accepted command');cmd=pending;pending=None
    got,error,sat=int(m[2],16),int(m[3]),int(m[4]);require(int(m[1])>cmd['cycle'],'native response did not follow acceptance')
    pair=dict(command=cmd,response_cycle=int(m[1]),data=got,error=error,sat=sat);pairs.append(pair)
    if cmd['op']==12:
     legal=direct==1 and 1<=cmd['count']<=8 and cmd['param']==0 and cmd['aux']==0 and cmd['data']>>(16*cmd['count'])==0
     require(error==int(not legal) and sat==0,'native op12 error/saturation contract')
     expect=0
     if legal:
      for i in range(cmd['count']):
       word=(cmd['data']>>(16*i))&65535;x=word-65536 if word&32768 else word
       expect|=exponential(x,lut)<<(16*i);domain.add(word);numeric+=1
     require(got==expect,'independent native op12 LUT result mismatch')
   m=VENDOR.fullmatch(s)
   if m:
    time,action,bank,row,value=int(m[1]),m[2],int(m[3]),int(m[4],2),int(m[5],2)
    if time!=last_vendor_time:last_bank_event=set();last_vendor_time=time
    require(bank not in last_bank_event,'one physical1RW bank used twice in same vendor event time');last_bank_event.add(bank)
    key=(bank,row)
    if action=='Writing':memory[key]=value;vendor_writes+=1
    else:
     # Some unrelated legacy tests read random pre-init locations. The active
     # full-U program initializes every location it reads; enforce it there.
     if kind=='full_U':require(key in memory,'full U read uninitialized physical SRAM word')
     if key in memory:require(memory[key]==value,'physical SRAM read differs from most recent write')
     vendor_reads+=1
   if s.startswith(('NEXP_','STATELESS_PASS ','GROUP_GATE_PASS ')):
    prefix=s.split(' ',1)[0];markers.setdefault(prefix,[]).append(numbers(s))
   if s.startswith('NEXP_COMPUTE ') and direct==1:
    require(len(pairs)>=2,'compute measurement has no actual native packets')
    a,b=pairs[-2:];q=numbers(s)
    require(a['command']['op']==b['command']['op']==12 and a['command']['count']==b['command']['count']==q['count'],'timing row not bound to two actual op12 packets')
    require(b['command']['cycle']-a['command']['cycle']==q['accepted_to_next_accept_cycles'],'fee not actual native/wrapper consecutive acceptance interval')
   if s.startswith('NEXP_FULL_U ') and direct==1:
    require(pairs and pairs[-1]['command']['op']==12,'full U timing not actual op12')
 if pending is not None:aborted.append(pending)
 require(all((direct==0 and kind in ('compute','full_U')) or c['op']==12 for c in aborted),'unfinished ordinary native command outside fixed reset sequence')
 require(len(aborted)<=({'compute':1,'full_U':1,'stateless':12}.get(kind,0)),'too many native cancellations for frozen reset program')
 if kind in ('compute','full_U','stateless'):
  lp=markers.get('NEXP_LANE_PATH',[]);hc=markers.get('NEXP_LANE_COUNT',[])
  require(len(lp)==1 and len(hc)==8 and {q['count'] for q in hc}==set(range(1,9)),'missing real CALC proof')
  lp=lp[0];valid=[p for p in pairs if p['command']['op']==12 and p['error']==0]
  require(lp['direct_mode']==direct and lp['direct_lanes']==lanes,'CALC selector drift')
  require(lp['checked_commands']==lp['op12_completed']==len(valid),'completed CALC count differs from actual responses')
  for q in hc:
   n=q['count'];c=sum(p['command']['count']==n for p in valid)
   require(q['commands']==c and q['calc_steps']==c*((n+lanes-1)//lanes),'CALC count histogram/steps drift')
  require(sum(q['calc_steps'] for q in hc)==lp['calc_steps'],'CALC total steps drift')
  if direct and kind in ('compute','full_U'):require(all(q['commands']>0 for q in hc),'missing n1..8 actual CALC coverage')
  np=markers.get('NEXP_NATIVE_PATH',[])
  if kind!='stateless':
   require(len(np)==1 and np[0]['direct_mode']==direct,'actual native path marker absent')
   require(np[0]['op12_commands']==sum(q['op']==12 for q in native_commands),'accepted op12 marker differs from raw commands')
   require(np[0]['other_commands']==sum(q['op']!=12 for q in native_commands),'ordinary native marker differs from raw commands')
  if direct and kind=='compute':
   # The unchanged adapter clamps all nonnegative S16 inputs to zero before
   # native op12. The external bench still tests all 65536 inputs; raw native
   # traces can independently prove only all negative S16 values plus zero.
   require(domain=={0}|set(range(32768,65536)),'raw native results do not cover the complete clamped S16 domain')
 return dict(events=events,old=old,markers=markers,numeric_values=numeric,unique_S16_values=len(domain),
  native_accepted=len(native_commands),native_completed=len(pairs),native_reset_cancellations=len(aborted),
  physical_reads=vendor_reads,physical_writes=vendor_writes,
  numerical_evidence='independent integer-LUT oracle for every completed native op12; outer NX32 format/persistent/reset/held-ACK assertions bound to source+PASS')

def audit(runroot,out,expected_result=None):
 runroot,out=Path(runroot).resolve(),Path(out).resolve();receipts=runroot/'receipts';results=receipts/'results'
 result_path=results/'result.json';result=json.loads(result_path.read_bytes());result_sha=sha(result_path)
 if expected_result:require(result_sha==expected_result,'actual result SHA drift')
 require(result.get('passed') is True and not any(result.get(k) for k in ('error','errors','traceback')),'result not successful')
 require(result['source_commit']==SOURCE,'run22 source commit drift')
 require(sha(runroot/'payload.tar')==PAYLOAD,'original run22 payload drift')
 require(sha(runroot/'receipts.tar')==ARCHIVE,'original run22 collected archive drift')
 manifest=json.loads((receipts/'inputs.json').read_bytes())
 require(manifest['source_commit']==SOURCE and manifest['payload_sha256']==PAYLOAD,'deployment source/payload identity drift')
 require(sha(receipts/'inputs.json')==result['manifest_sha256'] and (receipts/'inputs.json').read_bytes()==(runroot/'inputs.json').read_bytes(),'local/server manifest drift')
 require(result['prior_calibration_result_sha256']==PRIOR and result['prior_observed_sha256']==OBSERVED,'prior identities drift')
 require(result['native_N_instances']==1 and result['physical_qualified'] is False,'resource qualification drift')
 require(result['bank_sha256']==BANK,'frozen actual SRAM macro identity drift')
 tools=hashes(receipts/'tools.sha256')
 require(len(tools)==3 and tools['/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v']==BANK,'actual tools/bank receipt incomplete')
 require(all(result['gates'].get(k) is True for k in GATES),'required R4 gate missing')
 require('101884|mdt-r4-nexp-rtl|COMPLETED|0:0|' in (receipts/'sacct.txt').read_text(),'job terminal state/exit mismatch')
 allocation=(receipts/'allocation.txt').read_text()
 require(all(s in allocation for s in ('JobId=101884','Partition=c64','NodeList=node1','NumCPUs=4','CPUs/Task=4','NumTasks=1')),'actual allocation mismatch')
 reviewed={};hm=hashes(receipts/'output-files.sha256');verified=0
 for path in receipts.rglob('*'):
  if path.is_file() and path.relative_to(receipts).as_posix() in hm:
   require(sha(path)==hm[path.relative_to(receipts).as_posix()],'collected original output SHA drift '+str(path));verified+=1
 with tarfile.open(runroot/'payload.tar') as tar:
  def member(name):
   h=tar.extractfile(name);require(h is not None,'missing original payload '+name);return h.read()
  for field,prefix in (('code_sha256','source/'),('input_sha256','')):
   for name,digest in manifest[field].items():require(hashlib.sha256(member(prefix+name)).hexdigest()==digest,'payload member SHA drift '+name)
  lut_text=member('source/project/rtl/block_v2/block_v2_n_exp.svh').decode()
  lut={int(a):int(b) for a,b in re.findall(r"11'd(\d+):exp_lut=16'd(\d+)",lut_text)}
  require(set(lut)==set(range(1025)),'frozen EXP LUT incomplete')
  prior=json.loads(member('run18-result.json'));projection=json.loads(member('run18-observed.json'))
 require(manifest['input_sha256']=={'run18-result.json':PRIOR,'run18-observed.json':OBSERVED},'input lock drift')
 require(result['rtl_source_sha256']=={k:manifest['code_sha256'][k] for k in result['rtl_source_sha256']},'RTL result/source manifest map drift')
 require(result['rtl_source_sha256']['project/rtl/block_v2/block_v2_n.sv']==NATIVE_SHA and result['rtl_source_sha256']['project/rtl/pu_leaf_base/pu_u_group.sv']==U_SHA,'exact R4 RTL drift')
 require(projection['source_result_sha256']==PRIOR and len(projection['runs'])==21,'prior projection incomplete')
 old_events={}
 for q in projection['runs']:
  r=[r for r in prior['runs'] if (r['label'],r['mode'],r['seed'])==(q['label'],q['mode'],q['seed'])]
  require(len(r)==1 and r[0]['log_sha256']==q['log_sha256'] and r[0]['log']==q['log'],'prior original log provenance drift')
  old_events[q['label'],q['mode'],q['seed']]=q['observed']
 generation=result['generation']
 require(generation['integrated_production'] is True and generation['generated_sha256']=={'block_v2_n.sv':NATIVE_SHA,'pu_u_group.sv':U_SHA},'actual production/generator identity drift')
 for name,digest in generation['bench_sha256'].items():require(sha(results/'generated'/name)==digest,'actual generated bench/source SHA differs from measurement receipt')
 commands=result['commands'];require(len(commands)==85,'21 builds+63 runs+1 lint command count')
 require(len({c['log'] for c in commands})==len(commands),'command log collision')
 nonzero=[c for c in commands if c['exit_code']!=0]
 require(len(nonzero)==3,'exactly three illegal-lane negative executions required')
 for c in nonzero:
  require(c.get('expected_failure') is True and c.get('expected_error')=='NEXP_DIRECT_LANES must be exactly 2 or 4','unapproved failing command')
  require(re.fullmatch(r'illegal_lanes-(?:1-143|2-143|2-144)\.log',c['log']) is not None,'unexpected negative command identity')
 for c in commands:
  path=results/c['log'];require(sha(path)==c['log_sha256']==hm['results/'+c['log']],'command/log SHA mismatch')
  if c['log'].endswith('-build.log'):
   args=c['command'];require(args.count('-j')==1 and 1<=int(args[args.index('-j')+1])<=4,'compile worker allocation exceeded')
 rows=result['runs'];require(len(rows)==63 and {(r['label'],r['mode'],r['seed']) for r in rows}=={(l,m,s) for l in LABELS for m,s in SEEDS},'exact run/config/seed coverage drift')
 parsed={};audit_rows=[];active_ms={'compute_s16':[],'compute_s32':[],'full_U':[]}
 for row in rows:
  label,mode,seed=row['label'],row['mode'],row['seed'];path=results/row['log']
  require(row['passed'] is True,'unpassed individual run')
  command=[c for c in commands if (c['log'],c['log_sha256'],c['command'])==(row['log'],row['log_sha256'],row['command'])]
  require(len(command)==1,'run not bound to unique actual command');reviewed['results/'+row['log']]=sha(path)
  if label=='illegal_lanes':
   text=path.read_text();require(command[0]['exit_code']!=0 and row.get('expected_rejection') is True and 'NEXP_DIRECT_LANES must be exactly 2 or 4' in text,'directed negative was not detected')
   audit_rows.append(dict(label=label,mode=mode,seed=seed,expected_rejection=True));continue
  require(command[0]['exit_code']==0,'unapproved nonzero positive run')
  kind='compute' if 'compute' in label else 'full_U' if 'full_U' in label else 'stateless' if 'stateless' in label else 'legacy'
  parsed[label,mode,seed]=p=parse_log(path,lut,row.get('direct_mode',0),row['direct_lanes'],kind)
  if label in OLD_LABEL:require(p['old']==old_events[OLD_LABEL[label],mode,seed],'all actual run18 observable trace equality failed '+label)
  if label in MATCHES:require(p['events']==parsed[MATCHES[label],mode,seed]['events'],'fresh exact-R2 default/DIRECT0 full handshake trace equality failed '+label)
  if label=='direct_batch':require(ordinary(p['old'])==ordinary(parsed['baseline_batch',mode,seed]['old']),'enabled ordinary N changed')
  if kind=='compute':
   require(p['markers'].get('NEXP_COMPUTE_PASS')==[row['checks']] and row['checks']['values']>=65536,'numeric PASS binding failed')
   ms=p['markers'].get('NEXP_COMPUTE',[]);require(len(ms)==12 and {(q['mode32'],q['count']) for q in ms}=={(0,n) for n in range(1,9)}|{(1,n) for n in range(1,5)},'actual compute calibration count coverage')
   if label=='compute':
    for q in ms:active_ms['compute_s32' if q['mode32'] else 'compute_s16'].append((row,q))
  elif kind=='full_U':
   require(p['markers'].get('NEXP_U_PASS')==[row['checks']],'full U PASS binding failed')
   ms=p['markers'].get('NEXP_FULL_U',[]);require(len(ms)==12,'full U profile incomplete')
   for q in ms:require(q['S_reads']==q['S_writes']==1 and q['accepted_to_done_cycles']==q['input_stage_cycles']+q['compute_stage_cycles']+q['output_stage_cycles'],'full U real S stages not conserved')
   if label=='full_U':
    for q in ms:active_ms['full_U'].append((row,q))
  elif kind=='stateless':require(p['markers'].get('STATELESS_PASS')==[row['checks']] and row['checks']=={'cases':12,'checks':102,'reset_cases':12},'persistent/reset checks drift')
  elif label=='group_gate':require(p['markers'].get('GROUP_GATE_PASS')==[{'combinations':4}],'group flag gate PASS missing')
  else:require(ordinary(p['old']),'ordinary N functional evidence missing')
  if kind in ('compute','full_U','stateless'):
   require(p['markers']['NEXP_LANE_PATH']==[row['lane_path']] and p['markers']['NEXP_LANE_COUNT']==row['lane_counts'],'raw CALC markers/report differ')
   if label in ('compute','full_U','stateless'):
    require(row['direct_mode']==1 and row['direct_lanes']==4 and row['native_path']['op12_lanes4_commands']==row['lane_path']['checked_commands'],'active lane4 identity mismatch')
  audit_rows.append(dict(label=label,mode=mode,seed=seed,**{k:p[k] for k in ('numeric_values','unique_S16_values','native_accepted','native_completed','native_reset_cancellations','physical_reads','physical_writes')}))
 for name,rows_ms in active_ms.items():
  saved=result['measurements'][name];require(len(saved)==len(rows_ms),'saved measured rows count mismatch')
  for r,q in rows_ms:
   bound=[v for v in saved if (v['mode'],v['seed'],v['mode32'],v['count'])==(r['mode'],r['seed'],q['mode32'],q['count'])]
   require(len(bound)==1 and all(bound[0][k]==v for k,v in q.items()),'saved fee/stage differs from raw measured line')
   require(bound[0]['log_sha256']==r['log_sha256'] and bound[0]['command']==r['command'] and bound[0]['direct_mode']==1 and bound[0]['direct_lanes']==4,'measurement provenance/lane identity drift')
 fees={n:{q['accepted_to_next_accept_cycles'] for _,q in active_ms['compute_s32'] if q['count']==n} for n in range(1,5)}
 require(all(len(v)==1 for v in fees.values()),'actual lane4 costs nondeterministic');fees={n:next(iter(v)) for n,v in fees.items()}
 profile=result['profile'];require(profile['implementation']=='native_stateless_relative_exp_op12_lanes4' and profile['direct_lanes']==4 and profile['payload_contract']=='signed low16 of each S32 container, U16 zeroextend to S32','profile implementation/payload changed')
 require(len(profile['rows'])==8 and profile['passed'] is True,'profile count coverage incomplete')
 for n,q in enumerate(profile['rows'],1):
  sub=[n] if n<=4 else [4,n-4]
  require(q['count']==n and q['subcounts']==sub and q['charge_cycles']==sum(fees[i] for i in sub) and q['mode']=='legacy_s32_low16_zeroextend_stateless_op12_lanes4','profile not actual finite NX32 subframe fee')
 metadata={name:sha(receipts/name) for name in ('results/result.json','inputs.json','sacct.txt','allocation.txt','output-files.sha256','tools.sha256')}
 findings=dict(passed=True,source_commit=SOURCE,result_sha256=result_sha,payload_sha256=PAYLOAD,collected_archive_sha256=ARCHIVE,job='101884',
  allocation='c64/node1/4CPU',collected_original_output_SHA_checked=verified,code_members_SHA_checked=len(manifest['code_sha256']),
  output_manifest_entries=len(hm),outputs_not_collected_not_locally_read=len(hm)-verified,
  receipt_files_present=sum(f.is_file() for f in receipts.rglob('*')),metadata_files_parsed=metadata,
  payload_members_parsed={n:manifest['input_sha256'][n] for n in manifest['input_sha256']}|{'source/project/rtl/block_v2/block_v2_n_exp.svh':manifest['code_sha256']['project/rtl/block_v2/block_v2_n_exp.svh']},
  input_members_SHA_checked=len(manifest['input_sha256']),actual_runs=63,builds=21,positive_runs=60,expected_illegal_lane_failures=3,
  numeric_native_values=sum(q.get('numeric_values',0) for q in audit_rows),raw_files_parsed=reviewed,runs=audit_rows,
  NX32_frame_fees=fees,profile_fees=[q['charge_cycles'] for q in profile['rows']],
  actual_scope='native op12 entire clamped S16 domain (all negative values plus zero) integer-LUT proof; original external65536/NX32/full-U/state/lifecycle assertions; not generic S32 exp or end-to-end LLM RTL proof',
  reset_caveat='R4_TRACE does not encode reset edges; cancelled native requests are bounded by frozen reset stimuli and PASS. No independent reset waveform reconstruction claimed.',
  audit_correction='Initial independent audit incorrectly expected65536 unique native inputs. Unchanged adapter clamps nonnegative S16 to0: corrected native-domain assertion to negative32768 plus0; external65536 coverage remains frozen bench+PASS. No RTL/test receipt/source changed.',
  physical_qualified=False,SRAM_expansion=False)
 out.mkdir(parents=True,exist_ok=True);(out/'audit.json').write_bytes((json.dumps(findings,indent=2)+'\n').encode())
 text=f'''# run22 独立只读审计\n\n结论：PASS。源码 `{SOURCE}`，结果 SHA `{result_sha}`，作业 101884 实际 COMPLETED 0:0，c64/node1/4 核。\n\n核对全部 {verified} 份已回收原输出 SHA、{len(manifest['code_sha256'])} 项实际 payload 源及两项输入。63 次运行中 60 次成功，3 次 LANES3 以固定错误文本实际非零退出；其余 82 条 build/lint/run 命令必须成功。未运行 EDA，未复制原始日志。\n\n默认两 lane 四类及 DIRECT0 四 lane 与 fresh exact-R2 数据/周期握手 trace 精确相等；全部原可观察事件接回实际 run18 投影及原 log SHA。普通 N 接受至完成、元数据、结果保持。\n\n逐个完成的原生 op12 由独立整数 LUT oracle 重算，共 {findings['numeric_native_values']} 个元素。冻结 adapter 会把所有非负 S16 钳到0，因此每个 active compute raw trace 独立覆盖的是全部32768个负值及0（32769唯一输入）；外层完整65536输入逐值比较由冻结 bench 循环与实际 PASS 支撑，不能把 raw native trace 冒称65536唯一值。逐 count CALC 直方图与实际完成响应数/ceil(n/4) 一致。NX32 n1..4 实际费用 {list(fees.values())}，模型 n1..8 费用 {findings['profile_fees']}；n5..8 仍付两次有限 S32 帧费用，未借用 packedS16 n8 单次费用。\n\nfull U 原始物理 SRAM 读回核对最近写入，每条测量一读一写、分项 wall 守恒；stateless 12 场景/102 断言/12 reset 点绑定固定 bench 与实际 PASS。R4_TRACE 没有 reset 边标记，因此数值重算对取消请求仅按固定 reset 程序限定，不宣称从日志重建 reset 波形或所有持久状态。held ACK、非法尾 lane、外层 NX32 格式由已冻结 bench 断言与实际 PASS 支撑。\n\n未获得 STA、物理面积或 300MHz 资格；没有 SRAM 扩容或端到端大模型 RTL 证明。实际逐文件审核范围与 SHA 见 audit.json 的 raw_files_parsed；其它已回收文件只做 SHA 核对，未声称逐文件语义审核。\n'''
 text+=f"\n完整输出清单 {len(hm)} 项，其中本地回收并验 SHA 为 {verified} 项；其余 {len(hm)-verified} 项对象/二进制留在服务器，本审计未读取其内容，不把清单中的 SHA 当成本地重新计算。回收目录实际 {findings['receipt_files_present']} 个文件，63 份运行原 log 逐行语义解析；6 份关键 metadata 与 payload 内 LUT/两个 run18 输入另行列 SHA。63,447,040B 回收归档 SHA 已实算为 `{ARCHIVE}`。\n\n审计修正记录：初稿曾误要求原生端 65536 唯一输入，读回冻结 adapter 的 clamp 合同后改为32768负值加0；外层完整65536输入测试仍不变。仅修正独立审计断言/说明，没有修改生产或已测 bench 源。\n"
 (out/'audit.md').write_bytes(text.encode());return findings

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--result-sha')
 a=p.parse_args();r=audit(a.run,a.out,a.result_sha);print(json.dumps({k:r[k] for k in ('passed','result_sha256','actual_runs','numeric_native_values','profile_fees')}))
