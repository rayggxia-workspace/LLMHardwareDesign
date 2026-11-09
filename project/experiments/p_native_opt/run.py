"""Server-only native P optimization regression; no token/s extrapolation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
V=Path('/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator')
BANK=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
BANK_SHA='6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
SOURCES=[
 'project/rtl/block_local_s/block_local_s_arbiter.sv',
 'project/rtl/block_local_s/popt_s_policy_arbiter.sv',
 'project/rtl/s_sram/block_feed_s16k_sram.sv',
 'project/rtl/s_sram/block_feed_s16k_bank_rw.sv',
 'project/rtl/s_sram/local_s_p.sv',
 'project/rtl/block_feed_v1/block_feed_loader.sv',
 'project/rtl/block_v2/block_v2_m.sv',
 'project/rtl/block_v2/block_v2_m_context.sv',
 'project/rtl/block_v2/block_v2_g.sv',
 *['project/rtl/pu_leaf_base/'+s+'.sv' for s in
   ('pu_p_group','pu_p_store_control','pj_feed_hold','pj_mem_port','pj_sram_client')],
]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True)
 p.add_argument('--out',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
 p.add_argument('--workers',type=int,default=4);a=p.parse_args()
 a.repo=a.repo.resolve();a.out=a.out.resolve();a.manifest=a.manifest.resolve()
 if not 1<=a.workers<=int(os.environ.get('SLURM_CPUS_PER_TASK','0')):raise ValueError('Slurm CPU allocation required')
 if sha(BANK)!=BANK_SHA:raise ValueError('SRAM macro identity drift')
 manifest=json.loads(a.manifest.read_text());commit=manifest['source_commit']
 if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('real source commit required')
 for name,digest in manifest['code_sha256'].items():
  if sha(a.repo/name)!=digest:raise ValueError('source deployment drift '+name)
 a.out.mkdir(parents=True,exist_ok=False)
 report=dict(passed=False,source_commit=commit,scope='actual native S16/S64 P RTL, fixed four 1RW banks; no physical/full-model token/s qualification',
  manifest_sha256=sha(a.manifest),bank_sha256=sha(BANK),versions={'python':platform.python_version()},commands=[],components={},errors=[])
 def execute(command,log):
  command=list(map(str,command));start=time.monotonic()
  result=subprocess.run(command,cwd=a.repo,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  target=a.out/log;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(result.stdout)
  report['commands'].append(dict(command=command,exit_code=result.returncode,seconds=time.monotonic()-start,log=log,sha256=sha(target)))
  if result.returncode:raise RuntimeError(log+' exit '+str(result.returncode)+'\n'+result.stdout.decode(errors='replace')[-2000:])
  return result.stdout.decode(errors='replace')
 def component(name,call):
  try:
   value=call();report['components'][name]=value
  except Exception as error:
   report['errors'].append(dict(component=name,error=repr(error),traceback=traceback.format_exc()))
   print('COMPONENT_FAILED '+name+' '+repr(error),flush=True)
  (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 def subrunner(name,script,args):
  execute([sys.executable,'-B',HERE/script,'--repo',a.repo,'--out',a.out/name,*args],name+'-runner.log')
  result=json.loads((a.out/name/'result.json').read_text())
  if not result['passed']:raise ValueError(name+' did not pass')
  return dict(passed=True,result=name+'/result.json',sha256=sha(a.out/name/'result.json'))
 def group():
  measurements=[];runs=[]
  configurations=[('legacy',0,0),('context',1,0),('combined',1,1)]
  for label,opt,bank_rw in configurations:
   top='tb_popt_group';obj=a.out/('obj-group-'+label)
   execute([V,'--binary','--timing','--assert','--timescale','1ns/1ps','-Wno-fatal',
    '--x-initial','unique','--x-assign','unique','-j',a.workers,
    '-I'+str(a.repo/'project/rtl/block_v2'),'--top-module',top,'--Mdir',obj,
    '-GOPT='+str(opt),'-GBANK_RW='+str(bank_rw),HERE/(top+'.sv'),*[a.repo/s for s in SOURCES],BANK],label+'-group-build.log')
   for mode,seed in ((1,143),(2,143),(2,144)):
    log=f'{label}-group-{mode}-{seed}.log'
    output=execute([obj/('V'+top),f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],log)
    found=re.findall(r'^METRIC P_GROUP opt=(\d+) bank_rw=(\d+) cycles=(\d+) A=(\d+) B=(\d+) wide=(\d+) stores=(\d+)$',output,re.M)
    if len(found)!=1 or 'PASS P_GROUP native S' not in output:raise ValueError('group receipt incomplete')
    row=dict(zip(('opt','bank_rw','cycles','A','B','wide','stores'),map(int,found[0])))
    if (row['opt'],row['bank_rw'],row['A'],row['B'],row['wide'],row['stores'])!=(opt,bank_rw,2 if opt else 16,16,18 if opt else 32,16):
     raise ValueError('group work conservation')
    measurements.append(dict(label=label,mode=mode,seed=seed,**row));runs.append(log)
  for label,opt,bank_rw in (('default',0,0),('enabled',1,1)):
   # Unchanged original full-P program, including M->G routing and errors.
   top='tb_pu_p_group';bench=a.repo/'project/experiments/pu_leaf_base'/('tb_pu_p_group.sv')
   text=bench.read_text()
   if opt:
    old='pu_p_group dut(';assert text.count(old)==1
    text=text.replace(old,'pu_p_group #(.S_CONSUMER_PRIORITY(1),.S_BANK_RW(1),.M_CONTEXTS(8)) dut(')
   rendered=a.out/('legacy-'+label+'.sv');rendered.write_text(text)
   obj=a.out/('obj-legacy-'+label)
   execute([V,'--binary','--timing','--assert','--timescale','1ns/1ps','-Wno-fatal',
    '--x-initial','unique','--x-assign','unique','-j',a.workers,
    '-I'+str(a.repo/'project/rtl/block_v2'),'--top-module',top,'--Mdir',obj,
    rendered,*[a.repo/s for s in SOURCES],BANK],label+'-legacy-build.log')
   for mode,seed in ((1,143),(2,143),(2,144)):
    log=f'{label}-legacy-{mode}-{seed}.log'
    output=execute([obj/('V'+top),f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],log)
    if 'PASS P16 feed' not in output:raise ValueError('old P program receipt missing')
    runs.append(log)
  return dict(passed=True,measurements=measurements,logs=runs)
 report['versions']['verilator']=execute([V,'--version'],'verilator-version.log').strip()
 report['versions']['gcc']=execute(['g++','--version'],'gcc-version.log').splitlines()[0]
 component('policy',lambda:subrunner('policy','run_policy_rtl.py',['--workers',a.workers]))
 component('memory',lambda:subrunner('memory','run_memory.py',['--workers',a.workers,'--manifest',a.manifest]))
 component('context',lambda:subrunner('context','run_context.py',['--cpus',a.workers,'--verilator',V]))
 component('group',group)
 report['passed']=not report['errors'] and len(report['components'])==4
 (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(passed=report['passed'],source_commit=commit,errors=report['errors'],result=str(a.out/'result.json'))),flush=True)
 if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
