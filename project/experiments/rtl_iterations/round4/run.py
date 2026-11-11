"""Server Slurm only: R4 real-N/U tests, exact R2 comparison, measured fees."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import traceback
from prepare import prepare,sha,rtl_generator,HERE

BANK=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
BANK_SHA='6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
VERILATOR=Path('/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator')
RUN18_SHA='fb0b4d0d1251140655feea5bd671c196e5ae13b1fd47066dc22d6e1e1a2eac78'
RUN18_OBSERVED_SHA='cc5e13093dd5269e8fcd473e56a524e7a3b4e21d426e064b48ed0fab1f080296'
RTL_PATHS=[
 'project/rtl/block_local_s/block_local_s_arbiter.sv',
 'project/rtl/s_sram/local_s_base.sv','project/rtl/s_sram/block_feed_s16k_sram.sv',
 'project/rtl/block_v2/block_v2_n.sv','project/rtl/block_v2/block_v2_n_group.sv','project/rtl/block_v2/block_v2_n_exp.svh',
 'project/rtl/block_v2/block_v2_e.sv','project/rtl/block_v2/block_v2_e_compact.sv',
 'project/rtl/pu_leaf_base/pu_u_group.sv','project/rtl/pu_leaf_base/ucf_s_compute_client.sv',
 'project/rtl/pu_leaf_base/pu_compact_e_service.sv','project/rtl/pu_leaf_base/pu_u_direct_pair.sv',
 'project/rtl/pu_leaf_base/pu_nexp_shared.sv','project/rtl/pu_leaf_base/nexp_batch_adapter.sv']
EXPECTED={(0,n) for n in range(1,9)}|{(1,n) for n in range(1,5)}
INITIALIZATIONS=((1,143),(2,143),(2,144))

def measurements(text,prefix):
 return [{k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
         for line in text.splitlines() if line.startswith(prefix+' ')]

def ordinary(events):
 out=[];pending=None
 for line in events:
  c=re.fullmatch(r'COMPAT CMD c=(\d+) lane=1 meta=([0-9a-fA-F]+) (.*)',line)
  d=re.fullmatch(r'COMPAT DONE c=(\d+) lane=1 (.*)',line)
  if c:
   if pending is not None:raise ValueError('overlapping ordinary N')
   pending=(int(c[1]),int(c[2],16),c[2]+' '+c[3])
  elif d:
   if pending is None:raise ValueError('unmatched ordinary N response')
   start,meta,fields=pending;pending=None
   if meta&15!=15:out.append((fields,int(d[1])-start,d[2]))
 if pending is not None:raise ValueError('unfinished ordinary N')
 return out

def observed(text,passive=True):
 """All native handshake data/cycles, physical SRAM events and old result rows.

 Tool trailers and new passive CALC summaries are excluded; no old semantic
 line is dropped. passive=False allows old run18 measurement/log summaries.
 """
 return [s for s in text.splitlines() if re.match(r'^\s*\d+ (Reading|Writing) ',s)
  or s.startswith(('COMPAT ','NEXP_COMPUTE ','NEXP_COMPUTE_PASS ','NEXP_FULL_U ',
   'NEXP_U_PASS ','NEXP_NATIVE_PATH ','STATELESS_PASS '))
  or (passive and s.startswith('R4_TRACE '))]

def lane_proof(text,lanes,direct,require_all_counts=False):
 rows=measurements(text,'NEXP_LANE_PATH');counts=measurements(text,'NEXP_LANE_COUNT')
 if len(rows)!=1 or len(counts)!=8 or {q['count'] for q in counts}!=set(range(1,9)):
  raise ValueError('actual native CALC proof absent')
 q=rows[0]
 if q['direct_mode']!=direct or q['direct_lanes']!=lanes or q['checked_commands']!=q['op12_completed']:
  raise ValueError('native CALC identity/count drift')
 if sum(c['commands'] for c in counts)!=q['checked_commands'] or sum(c['calc_steps'] for c in counts)!=q['calc_steps']:
  raise ValueError('CALC histogram not conserved')
 for c in counts:
  if c['calc_steps']!=c['commands']*((c['count']+lanes-1)//lanes):raise ValueError('CALC work did not use selected lane count')
 if direct:
  if q['checked_commands']<=0:raise ValueError('no successful op12 actual executions')
  if require_all_counts and any(c['commands']<=0 for c in counts):raise ValueError('op12 n1..8 tail coverage absent')
 elif q['checked_commands'] or q['calc_steps']:raise ValueError('DIRECT0 executed op12')
 return q,counts

def baseline_identity(prior,label,mode,seed,checks,rows=None):
 """Re-executed exact R2 program must also reproduce actual run18 receipts."""
 selected=[r for r in prior['runs'] if r['label']==label and r['mode']==mode and r['seed']==seed]
 if len(selected)!=1 or selected[0].get('passed') is not True:raise ValueError('run18 case identity missing '+label)
 if checks is not None and checks!=selected[0].get('checks'):raise ValueError('fresh R2 checks differ from run18 '+label)
 if rows is not None:
  collection=prior['measurements']['full_U'] if label=='full_U' else prior['measurements']['compute_s16']+prior['measurements']['compute_s32']
  old=[r for r in collection if (r['mode'],r['seed'])==(mode,seed)]
  fields=set(rows[0]);reduced=[{k:q[k] for k in fields} for q in old]
  if sorted(rows,key=lambda q:(q['mode32'],q['count']))!=sorted(reduced,key=lambda q:(q['mode32'],q['count'])):
   raise ValueError('fresh exact R2 measurements differ from run18 '+label)

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
 root=a.root.resolve();repo=root/'source';out=root/'results';cpus=int(os.environ.get('SLURM_CPUS_PER_TASK','0'))
 if not os.environ.get('SLURM_JOB_ID') or not 1<=cpus<=4:raise ValueError('actual Slurm allocation1..4cores required')
 manifest=json.loads((root/'inputs.json').read_text(encoding='utf8'))
 if not re.fullmatch('[0-9a-f]{40}',manifest.get('source_commit','')):raise ValueError('real source commit required')
 if not manifest.get('code_sha256') or not manifest.get('input_sha256'):raise ValueError('empty deployment lock')
 for field,base in (('code_sha256',repo),('input_sha256',root)):
  for name,digest in manifest[field].items():
   if sha(base/name)!=digest:raise ValueError('deployment SHA drift '+name)
 if not set(RTL_PATHS)<=set(manifest['code_sha256']):raise ValueError('RTL dependency missing deployment source lock')
 if sha(BANK)!=BANK_SHA:raise ValueError('actual SRAM bank drift')
 if manifest['input_sha256'].get('run18-result.json')!=RUN18_SHA or sha(root/'run18-result.json')!=RUN18_SHA:
  raise ValueError('actual run18 calibration identity drift')
 prior=json.loads((root/'run18-result.json').read_bytes())
 if prior.get('passed') is not True:raise ValueError('run18 not passed')
 if manifest['input_sha256'].get('run18-observed.json')!=RUN18_OBSERVED_SHA or sha(root/'run18-observed.json')!=RUN18_OBSERVED_SHA:
  raise ValueError('actual run18 original observable trace identity drift')
 projected=json.loads((root/'run18-observed.json').read_bytes())
 if projected['source_result_sha256']!=RUN18_SHA or len(projected['runs'])!=21:raise ValueError('run18 original trace projection incomplete')
 for q in projected['runs']:
  bound=[p for p in prior['runs'] if (p['label'],p['mode'],p['seed'])==(q['label'],q['mode'],q['seed'])]
  if len(bound)!=1 or (bound[0]['log'],bound[0]['log_sha256'])!=(q['log'],q['log_sha256']):raise ValueError('run18 trace projection provenance drift')
 prior_events={(q['label'],q['mode'],q['seed']):q['observed'] for q in projected['runs']}
 out.mkdir(exist_ok=False)
 report=dict(passed=False,source_commit=manifest['source_commit'],manifest_sha256=sha(root/'inputs.json'),
  prior_calibration_result_sha256=RUN18_SHA,prior_observed_sha256=RUN18_OBSERVED_SHA,
  scope='Actual four-lane stateless op12 in one N/U; no SRAM expansion or physical qualification',
  rtl_source_sha256={n:sha(repo/n) for n in RTL_PATHS},bank_sha256=BANK_SHA,native_N_instances=1,physical_qualified=False,
  commands=[],runs=[],measurements=dict(compute_s16=[],compute_s32=[],full_U=[]),baseline_measurements=dict(compute=[],full_U=[]),
  gates={n:False for n in ('compute_s32','full_U','numeric','lifecycle','default_compatibility','enabled_ordinary',
   'stateless_context_preservation','old_batch_compatibility','default_lanes2_compatibility','direct0_lanes4_compatibility','op12_lanes4_execution')},
  versions=dict(python=platform.python_version(),verilator=subprocess.check_output([VERILATOR,'--version'],text=True).strip(),
   gcc=subprocess.check_output(['g++','--version'],text=True).splitlines()[0]))
 def save():(out/'result.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
 def call(command,log,expected_error=None):
  command=list(map(str,command))
  with (out/log).open('w',encoding='utf8') as f:r=subprocess.run(command,cwd=repo,stdout=f,stderr=subprocess.STDOUT)
  record=dict(command=command,log=log,exit_code=r.returncode,log_sha256=sha(out/log));report['commands'].append(record)
  text=(out/log).read_text(encoding='utf8')
  if expected_error:
   if r.returncode==0 or expected_error not in text:raise RuntimeError('directed illegal-lane rejection missing '+log)
   record.update(expected_failure=True,expected_error=expected_error)
  elif r.returncode:raise RuntimeError('RTL command failed '+log)
  return text,record
 try:
  g=out/'generated';report['generation']=prepare(repo,g,True);generator=rtl_generator();base=generator.HERE/'baseline'
  r=repo/'project/rtl';u=r/'pu_leaf_base';n=r/'block_v2'
  common=[r/'block_local_s/block_local_s_arbiter.sv',r/'s_sram/local_s_base.sv',r/'s_sram/block_feed_s16k_sram.sv',
   n/'block_v2_n.sv',n/'block_v2_n_group.sv',n/'block_v2_e.sv',n/'block_v2_e_compact.sv',
   u/'ucf_s_compute_client.sv',u/'pu_compact_e_service.sv',u/'pu_u_direct_pair.sv',BANK]
  oldcommon=[base/'block_v2_n.sv' if x==n/'block_v2_n.sv' else x for x in common]
  extra=[u/'pu_nexp_shared.sv',u/'nexp_batch_adapter.sv'] # SHA-locked unchanged R2 sources.
  group=[u/'pu_u_group.sv',*common,*extra];oldgroup=[base/'pu_u_group.sv',*oldcommon,*extra]
  compute=[*extra,n/'block_v2_n.sv',n/'block_v2_n_group.sv'];oldcompute=[*extra,base/'block_v2_n.sv',n/'block_v2_n_group.sv']
  native=[n/'block_v2_n.sv',n/'block_v2_n_group.sv'];oldnative=[base/'block_v2_n.sv',n/'block_v2_n_group.sv']
  call([VERILATOR,'--lint-only','-Wall','--top-module','pu_nexp_shared','-GNEXP_DIRECT=1',*extra],'router-strict-lint.log')
  # Every build is sequential, -j<=allocation<=4. Same retained-warning policy
  # as original run18 full native sources; router separately has strict lint.
  jobs=[
   ('baseline_legacy','tb_pu_u_group','r2_r1_tb_legacy.sv',oldgroup,[],2,0),
   ('default_legacy','tb_pu_u_group','r2_r1_tb_legacy.sv',group,[],2,0),
   ('lanes4_legacy','tb_pu_u_group','tb_lanes4_legacy.sv',group,[],4,0),
   ('baseline_batch','tb_pu_u_group','r2_r1_tb_enabled_legacy.sv',oldgroup,[],2,0),
   ('disabled_batch','tb_pu_u_group','tb_disabled_legacy.sv',group,[],4,0),
   ('direct_batch','tb_pu_u_group','tb_direct_legacy.sv',group,[],4,1),
   ('baseline_compute','tb_nexp_compute','baseline_tb_nexp_compute.sv',oldcompute,[],2,1),
   ('default_compute','tb_nexp_compute','tb_nexp_compute.sv',compute,[],2,1),
   ('baseline_disabled_compute','tb_nexp_compute','baseline_tb_nexp_compute.sv',oldcompute,['-GDIRECT=0'],2,0),
   ('disabled_compute','tb_nexp_compute','tb_nexp_compute.sv',compute,['-GDIRECT=0','-GLANES=4'],4,0),
   ('compute','tb_nexp_compute','tb_nexp_compute.sv',compute,['-GLANES=4'],4,1),
   ('baseline_full_U','tb_nexp_u','baseline_tb_nexp_u.sv',oldgroup,[],2,1),
   ('default_full_U','tb_nexp_u','tb_nexp_u.sv',group,[],2,1),
   ('baseline_disabled_full_U','tb_nexp_u','baseline_tb_nexp_u.sv',oldgroup,['-GDIRECT=0'],2,0),
   ('disabled_full_U','tb_nexp_u','tb_nexp_u.sv',group,['-GDIRECT=0','-GLANES=4'],4,0),
   ('full_U','tb_nexp_u','tb_nexp_u.sv',group,['-GLANES=4'],4,1),
   ('baseline_stateless','tb_nexp_stateless','baseline_tb_nexp_stateless.sv',oldnative,[],2,1),
   ('default_stateless','tb_nexp_stateless','tb_nexp_stateless.sv',native,[],2,1),
   ('stateless','tb_nexp_stateless','tb_nexp_stateless.sv',native,['-GLANES=4'],4,1),
   ('group_gate','tb_nexp_group_gate','tb_nexp_group_gate.sv',group,['-GLANES=4'],4,None),
   ('illegal_lanes','tb_nexp_group_gate','tb_nexp_group_gate.sv',group,['-GLANES=3'],3,None)]
  old={}
  for label,top,bench,sources,params,lanes,direct in jobs:
   obj=out/('obj-'+label)
   call([VERILATOR,'--binary','--timing','--assert','--timescale','1ns/1ps','-Wall','-Wno-fatal',
    '--x-initial','unique','--x-assign','unique','-j',cpus,'-I'+str(n),'--top-module',top,*params,'--Mdir',obj,g/bench,*sources],label+'-build.log')
   for mode,seed in INITIALIZATIONS:
    log=f'{label}-{mode}-{seed}.log'
    text,cmd=call([obj/('V'+top),f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],log,
     'NEXP_DIRECT_LANES must be exactly 2 or 4' if label=='illegal_lanes' else None)
    row=dict(label=label,mode=mode,seed=seed,passed=True,direct_lanes=lanes,log=log,log_sha256=cmd['log_sha256'],command=cmd['command'])
    if direct is not None:row['direct_mode']=direct
    if label=='illegal_lanes':row['expected_rejection']=True;report['runs'].append(row);save();continue
    if '%Error' in text or 'FAIL' in text:raise ValueError('RTL failure marker '+log)
    key=(label,mode,seed);old[key]=observed(text)
    historical=dict(baseline_legacy='default',default_legacy='default',lanes4_legacy='default',
     baseline_batch='disabled_batch',disabled_batch='disabled_batch',baseline_compute='compute',default_compute='compute',
     baseline_disabled_compute='disabled_compute',disabled_compute='disabled_compute',baseline_full_U='full_U',default_full_U='full_U',
     baseline_disabled_full_U='disabled_full_U',disabled_full_U='disabled_full_U',baseline_stateless='stateless',default_stateless='stateless')
    if label in historical:
     if observed(text,False)!=prior_events[historical[label],mode,seed]:raise ValueError('complete original observable trace differs from run18 '+label)
     row.update(exact_run18_observed_match=True,run18_label=historical[label],run18_observed_sha256=RUN18_OBSERVED_SHA)
    if label in ('baseline_legacy','default_legacy','lanes4_legacy','baseline_batch','disabled_batch','direct_batch'):
     if 'PASS U native' not in text:raise ValueError('legacy functional gate absent')
     ev=[s for s in text.splitlines() if s.startswith('COMPAT ')]
     if not ev:raise ValueError('compatibility trace absent')
     if label in ('default_legacy','lanes4_legacy'):
      if old[key]!=old['baseline_legacy',mode,seed]:raise ValueError('default/disabled U ordinary trace changed')
      row['baseline_label']='baseline_legacy';row['exact_default_lanes2_match']=label=='default_legacy'
      if lanes==4:row['exact_direct0_lanes4_match']=True
     elif label=='disabled_batch':
      if old[key]!=old['baseline_batch',mode,seed]:raise ValueError('lane4 DIRECT0 full batch program differs')
      row.update(exact_old_batch_match=True,baseline_label='baseline_batch')
     elif label=='direct_batch':
      if ordinary(ev)!=ordinary(old['baseline_batch',mode,seed]):raise ValueError('lane4 direct ordinary N differs')
     row['compatibility_events']=len(ev);row['ordinary_N_commands']=len(ordinary(ev))
    elif 'compute' in label:
     proof=measurements(text,'NEXP_COMPUTE_PASS');ms=measurements(text,'NEXP_COMPUTE')
     if len(proof)!=1 or proof[0]['values']<65536 or len(ms)!=12 or {(q['mode32'],q['count']) for q in ms}!=EXPECTED:
      raise ValueError('compute coverage/calibration incomplete')
     row['checks']=proof[0]
     if label=='baseline_compute':
      baseline_identity(prior,'compute',mode,seed,proof[0],ms);report['baseline_measurements']['compute']+=ms
     elif label=='default_compute':
      if old[key]!=old['baseline_compute',mode,seed]:raise ValueError('default2 all compute handshakes differ from exact R2')
      row.update(exact_default_lanes2_match=True,baseline_label='baseline_compute')
     elif label=='baseline_disabled_compute':baseline_identity(prior,'disabled_compute',mode,seed,proof[0])
     elif label=='disabled_compute':
      if old[key]!=old['baseline_disabled_compute',mode,seed]:raise ValueError('DIRECT0 lane4 compute trace differs')
      row.update(exact_old_batch_match=True,baseline_label='baseline_disabled_compute')
     elif label=='compute':
      for q in ms:
       if q['accepted_to_next_accept_cycles']<=q['accepted_to_done_cycles']:raise ValueError('invalid measured interval')
       q.update(passed=True,direct_mode=1,direct_lanes=4,mode=mode,seed=seed,log=log,log_sha256=cmd['log_sha256'],command=cmd['command'])
       report['measurements']['compute_s32' if q['mode32'] else 'compute_s16'].append(q)
    elif 'full_U' in label:
     proof=measurements(text,'NEXP_U_PASS');ms=measurements(text,'NEXP_FULL_U')
     if len(proof)!=1 or len(ms)!=12 or {(q['mode32'],q['count']) for q in ms}!=EXPECTED:raise ValueError('fullU calibration incomplete')
     row['checks']=proof[0]
     for q in ms:
      if q['S_reads']!=1 or q['S_writes']!=1 or q['accepted_to_done_cycles']!=sum(q[f] for f in ('input_stage_cycles','compute_stage_cycles','output_stage_cycles')):
       raise ValueError('fullU stage/S work not conserved')
     if label=='baseline_full_U':baseline_identity(prior,'full_U',mode,seed,proof[0],ms);report['baseline_measurements']['full_U']+=ms
     elif label=='default_full_U':
      if old[key]!=old['baseline_full_U',mode,seed]:raise ValueError('default2 timed physical SRAM/native trace differs')
      row.update(exact_default_lanes2_match=True,baseline_label='baseline_full_U')
     elif label=='baseline_disabled_full_U':baseline_identity(prior,'disabled_full_U',mode,seed,proof[0])
     elif label=='disabled_full_U':
      if old[key]!=old['baseline_disabled_full_U',mode,seed]:raise ValueError('DIRECT0 lane4 fullU trace differs')
      row.update(exact_old_batch_match=True,baseline_label='baseline_disabled_full_U')
     elif label=='full_U':
      for q in ms:
       q.update(passed=True,direct_mode=1,direct_lanes=4,mode=mode,seed=seed,log=log,log_sha256=cmd['log_sha256'],command=cmd['command']);report['measurements']['full_U'].append(q)
    elif 'stateless' in label:
     proof=measurements(text,'STATELESS_PASS')
     if len(proof)!=1 or proof[0]['cases']<10 or proof[0]['reset_cases']!=12:raise ValueError('stateless/lifecycle proof absent')
     row['checks']=proof[0]
     if label=='baseline_stateless':baseline_identity(prior,'stateless',mode,seed,proof[0])
     elif label=='default_stateless':
      if old[key]!=old['baseline_stateless',mode,seed]:raise ValueError('default2 persistent/reset command trace differs')
      row.update(exact_default_lanes2_match=True,baseline_label='baseline_stateless')
    else:
     if measurements(text,'GROUP_GATE_PASS')!=[{'combinations':4}]:raise ValueError('BATCH/DIRECT gate proof absent')
    if 'compute' in label or 'full_U' in label or 'stateless' in label:
     lane,counts=lane_proof(text,lanes,direct,'compute' in label or 'full_U' in label)
     row.update(lane_path=lane,lane_counts=counts)
     paths=measurements(text,'NEXP_NATIVE_PATH')
     if 'stateless' not in label:
      if len(paths)!=1 or paths[0]['direct_mode']!=direct or bool(paths[0]['op12_commands'])!=bool(direct):raise ValueError('actual native direct marker mismatch')
      row['native_path']=paths[0]
     else:row['native_path']=dict(direct_mode=1)
     if lanes==4 and direct:row['native_path']['op12_lanes4_commands']=lane['checked_commands']
     if label=='compute' and row['native_path']['other_commands']!=0:raise ValueError('lane4 used four-command setup')
    report['runs'].append(row);save()
  fees={}
  for count in range(1,5):
   costs={q['accepted_to_next_accept_cycles'] for q in report['measurements']['compute_s32'] if q['count']==count}
   if len(costs)!=1:raise ValueError('nondeterministic actual lane4 fee '+str(count))
   fees[count]=costs.pop()
  report['profile']=dict(schema_version=1,passed=True,direct_lanes=4,
   scope='NExp supplemental compute wrapper service only; old vector_region unchanged',
   implementation='native_stateless_relative_exp_op12_lanes4',payload_contract='signed low16 of each S32 container, U16 zeroextend to S32',fallback_input_bits=[16],rows=[])
  for count in range(1,9):
   sub=[count] if count<=4 else [4,count-4]
   report['profile']['rows'].append(dict(count=count,charge_cycles=sum(fees[n] for n in sub),subcounts=sub,
    mode='legacy_s32_low16_zeroextend_stateless_op12_lanes4',derivation='sum of actual compute_s32 accepted_to_next_accept_cycles; excludes private-S stages'))
  report['gates']={k:True for k in report['gates']};report['passed']=True
 except Exception as e:report['error']=repr(e);report['traceback']=traceback.format_exc();raise
 finally:save()
 print('ROUND4_LANES4_U_PASS',flush=True)

if __name__=='__main__':main()
