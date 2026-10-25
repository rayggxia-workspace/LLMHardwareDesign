"""Server-only actual RTL boundary builds and execution; baseline failure is retained."""
import argparse,hashlib,json,subprocess,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('task',choices=['build','sim']);p.add_argument('--out',type=Path,required=True);p.add_argument('--build',type=Path);p.add_argument('--input',type=Path);p.add_argument('--baseline',action='store_true');p.add_argument('--stall',type=int,default=0);a=p.parse_args();bd=json.loads((ROOT/'binding.json').read_text());a.out.mkdir(exist_ok=False)
 for n,h in bd['sources'].items():
  if sha(ROOT/n)!=h:raise ValueError('source SHA')
 m={'status':'ERROR','source':bd,'task':a.task,'baseline':a.baseline,'stall':a.stall};prefix=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind','/public/home/yuzelu/opt/eda:/eda:ro','--pwd',str(a.out),'/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif']
 try:
  if a.task=='build':
   rtl=ROOT/'project/rtl/runtime_cache';sv=[rtl/n for n in('sfu84.sv','mul84.sv','norm84.sv','mfront85.sv')]+[HERE/'baseline-chain85.sv'if a.baseline else rtl/'chain85.sv',ROOT/'project/rtl/norm_service/store82.sv',ROOT/'project/rtl/wide_service/memory_link.sv'];args=['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','chain85','--prefix','Vchain85','--Mdir',a.out/'obj','-CFLAGS','-std=c++17 -O2',*sv,HERE/'boundary.cpp']
  else:
   b=json.loads((a.build/'manifest.json').read_text());im=json.loads((a.input/'manifest.json').read_text())
   if b['status']!='BOUNDARY_BUILT'or b['baseline']!=a.baseline or sha(a.build/'obj/Vchain85')!=b['binary_sha256']:raise ValueError('build binding')
   for e in im['artifacts']:
    if sha(a.input/e['path'])!=e['sha256']:raise ValueError('input SHA')
   m['build_manifest_sha256']=sha(a.build/'manifest.json');m['input_manifest_sha256']=sha(a.input/'manifest.json');args=[a.build/'obj/Vchain85',a.input/'vectors85.tsv',a.out/'actual.jsonl',a.stall]
  argv=[*prefix,*map(str,args)];start=time.monotonic()
  with (a.out/'execution.log').open('w')as f:r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,timeout=600,stdin=subprocess.DEVNULL)
  m.update(command=argv,exit=r.returncode,seconds=time.monotonic()-start)
  if a.task=='sim'and a.baseline:
   if r.returncode!=1 or 'terminal idle response discarded'not in(a.out/'execution.log').read_text():raise ValueError('baseline must expose exact real failure')
   m['status']='EXPECTED_ORIGINAL_RTL_TERMINAL_DISCARD_FAILURE'
  elif r.returncode:raise ValueError('execution failure')
  elif a.task=='build':m.update(status='BOUNDARY_BUILT',binary_sha256=sha(a.out/'obj/Vchain85'))
  else:m['status']='ACTUAL_RTL_BOUNDARY_EXECUTED_NOT_RECEIVED'
 except Exception as e:m['error']=str(e);m['traceback']=traceback.format_exc();raise
 finally:m['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in a.out.iterdir()if q.is_file()and q.name!='manifest.json'];put(a.out/'manifest.json',m)
 print(m['status'])
if __name__=='__main__':main()
