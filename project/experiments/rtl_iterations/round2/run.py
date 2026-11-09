"""Server-only real R2 native-U tests and measurement-derived service profile."""
import argparse
import hashlib
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
RUN16_SHA='78c57febe43f2a114a8a21ca9b5992b465d7b7589f05c83eb68e5f97923d4ef7'
RTL_PATHS=[
 'project/rtl/block_local_s/block_local_s_arbiter.sv',
 'project/rtl/s_sram/local_s_base.sv','project/rtl/s_sram/block_feed_s16k_sram.sv',
 'project/rtl/block_v2/block_v2_n.sv','project/rtl/block_v2/block_v2_n_group.sv','project/rtl/block_v2/block_v2_n_exp.svh',
 'project/rtl/block_v2/block_v2_e.sv','project/rtl/block_v2/block_v2_e_compact.sv',
 'project/rtl/pu_leaf_base/pu_u_group.sv','project/rtl/pu_leaf_base/ucf_s_compute_client.sv',
 'project/rtl/pu_leaf_base/pu_compact_e_service.sv','project/rtl/pu_leaf_base/pu_u_direct_pair.sv',
 'project/rtl/pu_leaf_base/pu_nexp_shared.sv','project/rtl/pu_leaf_base/nexp_batch_adapter.sv']
EXPECTED={(0,n) for n in range(1,9)}|{(1,n) for n in range(1,5)}

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

def observed(text):
 """Compare all timed SRAM events and semantic PASS/profile rows, excluding tool trailers."""
 return [s for s in text.splitlines() if re.match(r'^\s*\d+ (Reading|Writing) ',s)
         or s.startswith(('NEXP_COMPUTE ','NEXP_COMPUTE_PASS ','NEXP_FULL_U ','NEXP_U_PASS '))]

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
 if 'run16-result.json' not in manifest['input_sha256'] or sha(root/'run16-result.json')!=RUN16_SHA:raise ValueError('run16 calibration identity drift')
 prior=json.loads((root/'run16-result.json').read_text(encoding='utf8'))
 if prior.get('passed') is not True:raise ValueError('run16 not passed')
 out.mkdir(exist_ok=False)
 report=dict(passed=False,source_commit=manifest['source_commit'],manifest_sha256=sha(root/'inputs.json'),
  prior_calibration_result_sha256=RUN16_SHA,
  scope='Actual optional stateless relative EXP in one production N/U; no SRAM expansion or physical qualification',
  rtl_source_sha256={n:sha(repo/n) for n in RTL_PATHS},bank_sha256=BANK_SHA,native_N_instances=1,
  physical_qualified=False,commands=[],runs=[],measurements=dict(compute_s16=[],compute_s32=[],full_U=[]),
  baseline_measurements=dict(compute=[],full_U=[]),
  gates={n:False for n in ('compute_s32','full_U','numeric','lifecycle','default_compatibility','enabled_ordinary',
                         'stateless_context_preservation','old_batch_compatibility')},
  versions=dict(python=platform.python_version(),verilator=subprocess.check_output([VERILATOR,'--version'],text=True).strip(),
                gcc=subprocess.check_output(['g++','--version'],text=True).splitlines()[0]))
 def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
 def call(command,log):
  command=list(map(str,command))
  with (out/log).open('w',encoding='utf8') as f:r=subprocess.run(command,cwd=repo,stdout=f,stderr=subprocess.STDOUT)
  record=dict(command=command,log=log,exit_code=r.returncode,log_sha256=sha(out/log));report['commands'].append(record)
  if r.returncode:raise RuntimeError('RTL command failed '+log)
  return (out/log).read_text(encoding='utf8'),record
 try:
  g=out/'generated';report['generation']=prepare(repo,g,True);generator=rtl_generator();base=generator.HERE/'baseline'
  r=repo/'project/rtl';u=r/'pu_leaf_base';n=r/'block_v2'
  common=[r/'block_local_s/block_local_s_arbiter.sv',r/'s_sram/local_s_base.sv',r/'s_sram/block_feed_s16k_sram.sv',
   n/'block_v2_n.sv',n/'block_v2_n_group.sv',n/'block_v2_e.sv',n/'block_v2_e_compact.sv',
   u/'ucf_s_compute_client.sv',u/'pu_compact_e_service.sv',u/'pu_u_direct_pair.sv',BANK]
  oldcommon=[base/'block_v2_n.sv' if x==n/'block_v2_n.sv' else x for x in common]
  newextra=[u/'pu_nexp_shared.sv',u/'nexp_batch_adapter.sv'];oldextra=[base/'pu_nexp_shared.sv',base/'nexp_batch_adapter.sv']
  newgroup=[u/'pu_u_group.sv',*common,*newextra];oldgroup=[base/'pu_u_group.sv',*oldcommon,*oldextra]
  oldcompute=[*oldextra,base/'block_v2_n.sv',n/'block_v2_n_group.sv'];newcompute=[*newextra,n/'block_v2_n.sv',n/'block_v2_n_group.sv']
  call([VERILATOR,'--lint-only','-Wall','--top-module','pu_nexp_shared','-GNEXP_DIRECT=1',*newextra],'new-router-lint.log')
  directlegacy=(g/'r1_tb_enabled_legacy.sv').read_text(encoding='utf8')
  directlegacy=directlegacy.replace('pu_u_group #(.NEXP_BATCH(1)) dut (','pu_u_group #(.NEXP_BATCH(1),.NEXP_DIRECT(1)) dut (')
  (g/'tb_direct_legacy.sv').write_text(directlegacy,encoding='utf8')
  jobs=[
   ('legacy','tb_pu_u_group','r1_tb_legacy.sv',oldgroup,[]),
   ('default','tb_pu_u_group','r1_tb_legacy.sv',newgroup,[]),
   ('baseline_batch','tb_pu_u_group','r1_tb_enabled_legacy.sv',oldgroup,[]),
   ('disabled_batch','tb_pu_u_group','r1_tb_enabled_legacy.sv',newgroup,[]),
   ('direct_batch','tb_pu_u_group','tb_direct_legacy.sv',newgroup,[]),
   ('baseline_compute','tb_nexp_compute','r1_tb_nexp_compute.sv',oldcompute,[]),
   ('disabled_compute','tb_nexp_compute','tb_nexp_compute.sv',newcompute,['-GDIRECT=0']),
   ('compute','tb_nexp_compute','tb_nexp_compute.sv',newcompute,['-GDIRECT=1']),
   ('baseline_full_U','tb_nexp_u','r1_tb_nexp_u.sv',oldgroup,[]),
   ('disabled_full_U','tb_nexp_u','tb_nexp_u.sv',newgroup,['-GDIRECT=0']),
   ('full_U','tb_nexp_u','tb_nexp_u.sv',newgroup,['-GDIRECT=1']),
   ('stateless','tb_nexp_stateless','tb_nexp_stateless.sv',[n/'block_v2_n.sv',n/'block_v2_n_group.sv'],[]),
   ('group_gate','tb_nexp_group_gate','tb_nexp_group_gate.sv',newgroup,[])]
  originals={};batch_originals={};old_observed={}
  for label,top,bench,sources,params in jobs:
   obj=out/('obj-'+label)
   # Same retained-warning policy as run16's unchanged full native sources;
   # newly authored synthesizable router has a separate strict warning gate.
   call([VERILATOR,'--binary','--timing','--assert','--timescale','1ns/1ps','-Wall','-Wno-fatal',
         '--x-initial','unique','--x-assign','unique','-j',cpus,'-I'+str(n),'--top-module',top,*params,'--Mdir',obj,g/bench,*sources],label+'-build.log')
   for mode,seed in ((1,143),(2,143),(2,144)):
    log=f'{label}-{mode}-{seed}.log';text,cmd=call([obj/('V'+top),f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],log)
    if '%Error' in text or 'FAIL' in text:raise ValueError('RTL failure marker '+log)
    row=dict(label=label,mode=mode,seed=seed,passed=True,log=log,log_sha256=cmd['log_sha256'],command=cmd['command'])
    if label in ('legacy','default','baseline_batch','disabled_batch','direct_batch'):
     if 'PASS U native' not in text:raise ValueError('legacy functional gate absent')
     ev=[s for s in text.splitlines() if s.startswith('COMPAT ')]
     if not ev:raise ValueError('compatibility trace absent')
     if label=='legacy':originals[mode,seed]=ev
     elif label=='default' and ev!=originals[mode,seed]:raise ValueError('R2 default differs from R1 default')
     elif label=='baseline_batch':batch_originals[mode,seed]=ev
     elif label=='disabled_batch':
      if ev!=batch_originals[mode,seed]:raise ValueError('DIRECT0 differs from R1 BATCH1')
      row['exact_old_batch_match']=True;row['baseline_label']='baseline_batch'
     elif label=='direct_batch' and ordinary(ev)!=ordinary(batch_originals[mode,seed]):raise ValueError('direct ordinary N differs')
     row['compatibility_events']=len(ev);row['ordinary_N_commands']=len(ordinary(ev))
    elif 'compute' in label:
     proof=measurements(text,'NEXP_COMPUTE_PASS');ms=measurements(text,'NEXP_COMPUTE')
     if len(proof)!=1 or proof[0]['values']<65536 or len(ms)!=12 or {(q['mode32'],q['count']) for q in ms}!=EXPECTED:raise ValueError('compute coverage/calibration incomplete')
     row['checks']=proof[0]
     if label=='baseline_compute':
      old_observed[label,mode,seed]=observed(text)
      report['baseline_measurements']['compute']+=ms
      for q in ms:
       if q['mode32'] and q['accepted_to_next_accept_cycles']!=prior['profile']['rows'][q['count']-1]['charge_cycles']:raise ValueError('R1 service did not reproduce run16')
     elif label=='disabled_compute':
      if observed(text)!=old_observed['baseline_compute',mode,seed]:raise ValueError('DIRECT0 compute/functional trace differs from R1')
      row['exact_old_batch_match']=True;row['baseline_label']='baseline_compute'
     else:
      for q in ms:
       if q['accepted_to_next_accept_cycles']<=q['accepted_to_done_cycles']:raise ValueError('invalid compute initiation interval')
       q.update(passed=True,direct_mode=1,mode=mode,seed=seed,log=log,log_sha256=cmd['log_sha256'],command=cmd['command'])
       report['measurements']['compute_s32' if q['mode32'] else 'compute_s16'].append(q)
    elif 'full_U' in label:
     proof=measurements(text,'NEXP_U_PASS');ms=measurements(text,'NEXP_FULL_U')
     if len(proof)!=1 or len(ms)!=12 or {(q['mode32'],q['count']) for q in ms}!=EXPECTED:raise ValueError('fullU calibration incomplete')
     row['checks']=proof[0]
     for q in ms:
      if q['S_reads']!=1 or q['S_writes']!=1 or q['accepted_to_done_cycles']!=sum(q[f] for f in ('input_stage_cycles','compute_stage_cycles','output_stage_cycles')):raise ValueError('fullU stage work not conserved')
     if label=='baseline_full_U':old_observed[label,mode,seed]=observed(text);report['baseline_measurements']['full_U']+=ms
     elif label=='disabled_full_U':
      if observed(text)!=old_observed['baseline_full_U',mode,seed]:raise ValueError('DIRECT0 fullU SRAM/profile trace differs from R1')
      row['exact_old_batch_match']=True;row['baseline_label']='baseline_full_U'
     else:
      for q in ms:
       q.update(passed=True,direct_mode=1,mode=mode,seed=seed,log=log,log_sha256=cmd['log_sha256'],command=cmd['command']);report['measurements']['full_U'].append(q)
    elif label=='stateless':
     proof=measurements(text,'STATELESS_PASS')
     if len(proof)!=1 or proof[0]['cases']<10 or proof[0]['reset_cases']!=12:raise ValueError('stateless/lifecycle proof absent')
     row['checks']=proof[0];row['direct_mode']=1
    else:
     if measurements(text,'GROUP_GATE_PASS')!=[{'combinations':4}]:raise ValueError('BATCH/DIRECT gate proof absent')
    if label in ('disabled_compute','compute','disabled_full_U','full_U'):
     path=measurements(text,'NEXP_NATIVE_PATH');direct=int(label in ('compute','full_U'))
     if len(path)!=1 or path[0]['direct_mode']!=direct or bool(path[0]['op12_commands'])!=bool(direct):raise ValueError('actual native direct-path marker mismatch')
     if label=='compute' and path[0]['other_commands']!=0:raise ValueError('direct compute used legacy four-command sequence')
     row['direct_mode']=direct;row['native_path']=path[0]
    report['runs'].append(row);save()
  fees={}
  for count in range(1,5):
   observed_costs={q['accepted_to_next_accept_cycles'] for q in report['measurements']['compute_s32'] if q['count']==count}
   if len(observed_costs)!=1:raise ValueError('nondeterministic direct cost '+str(count))
   fees[count]=observed_costs.pop()
  report['profile']=dict(schema_version=1,passed=True,scope='NExp supplemental compute wrapper service only; old vector_region unchanged',
   implementation='native_stateless_relative_exp_op12',payload_contract='signed low16 of each S32 container, U16 zeroextend to S32',fallback_input_bits=[16],rows=[])
  for count in range(1,9):
   sub=[count] if count<=4 else [4,count-4]
   report['profile']['rows'].append(dict(count=count,charge_cycles=sum(fees[n] for n in sub),subcounts=sub,
    mode='legacy_s32_low16_zeroextend_stateless_op12',derivation='sum of actual compute_s32 accepted_to_next_accept_cycles; excludes private-S stages'))
  report['gates']={k:True for k in report['gates']};report['passed']=True
 except Exception as e:report['error']=repr(e);report['traceback']=traceback.format_exc();raise
 finally:save()
 print('ROUND2_STATELESS_U_PASS',flush=True)

if __name__=='__main__':main()
