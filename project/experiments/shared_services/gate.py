"""Exact mapped102, Liberty logic functions, unchanged behavioral store82; no delay/STA claim."""
import argparse,json,hashlib,subprocess,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
LIB=Path('/public/home/yuzelu/RuizhiLiang/issue80-block-circuit-20261025/nangate45-reference/NangateOpenCellLibrary_typical.lib')
SIF='/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif'
PREFIX=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind','/public/home/yuzelu/opt/eda:/eda:ro']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def load(p):return json.loads(Path(p).read_text())
def bound(p,status):
 m=load(p/'manifest.json')
 if m['status']!=status:raise ValueError('expected status '+status)
 for e in m['artifacts']:
  if sha(p/e['path'])!=e['sha256']:raise ValueError('artifact SHA '+e['path'])
 return m
def main():
 p=argparse.ArgumentParser();p.add_argument('task',choices=['prepare','build','sim']);p.add_argument('--out',type=Path,required=True);p.add_argument('--map',type=Path);p.add_argument('--prepared',type=Path);p.add_argument('--build',type=Path);p.add_argument('--input',type=Path);p.add_argument('--stall',type=int,default=0);p.add_argument('--pilot',type=int,default=1);a=p.parse_args();b=load(ROOT/'binding.json')
 for n,h in b['sources'].items():
  if sha(ROOT/n)!=h:raise ValueError('source SHA')
 a.out.mkdir(exist_ok=False);m={'status':'ERROR','source':b,'task':a.task,'suite':'pilot','stall':a.stall,'pilot':a.pilot,'library_sha256':sha(LIB)}
 def cmd(name,args):
  argv=[*PREFIX,'--pwd',str(a.out),SIF,*map(str,args)];start=time.monotonic()
  with(a.out/(name+'.log')).open('w')as f:r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=7000)
  put(a.out/(name+'-command.json'),{'argv':argv,'exit':r.returncode,'seconds':time.monotonic()-start})
  if r.returncode:raise ValueError('failed '+name)
 try:
  if a.task=='prepare':
   mm=bound(a.map,'LOGIC_ONLY_MAPPED_NOT_PPA')
   if mm['library_sha256']!=sha(LIB):raise ValueError('exact library')
   for n,h in mm['source']['sources'].items():
    if n.startswith('project/rtl/')and b['sources'].get(n)!=h:raise ValueError('mapped actual RTL source')
   m['mapping_manifest_sha256']=sha(a.map/'manifest.json');m['mapping_source']=mm['source'];(a.out/'mapped.json').write_bytes((a.map/'mapped.json').read_bytes())
   script=f'read_json {a.out}/mapped.json\nwrite_verilog -noattr -noexpr {a.out}/mapped.v\ndesign -reset\nread_liberty -ignore_miss_func -ignore_miss_dir {LIB}\nwrite_verilog -noattr {a.out}/cells.v\n';(a.out/'export.ys').write_text(script);cmd('export',['yosys','-s',a.out/'export.ys']);m['status']='EXACT_MAPPED106_LOGIC_EXPORTED'
  elif a.task=='build':
   pm=bound(a.prepared,'EXACT_MAPPED106_LOGIC_EXPORTED');cmd('build',['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','shared106','--prefix','Vshared106','--Mdir',a.out/'obj','--output-split','15000','--output-split-cfuncs','200','-CFLAGS','-std=c++17 -O2',a.prepared/'mapped.v',a.prepared/'cells.v',ROOT/'project/rtl/norm_service/store82.sv',ROOT/'project/experiments/shared_services/sim.cpp']);m['prepared_manifest_sha256']=sha(a.prepared/'manifest.json');m['binary_sha256']=sha(a.out/'obj/Vshared106');m['status']='GATE106_BUILT_NOT_EXECUTED'
  else:
   bm=bound(a.build,'GATE106_BUILT_NOT_EXECUTED');im=bound(a.input,'VERIFIED_PAYLOAD_REUSE_NOT_RTL')
   if sha(a.build/'obj/Vshared106')!=bm['binary_sha256']:raise ValueError('binary SHA')
   for n in ('project/experiments/shared_services/sim.cpp','project/rtl/norm_service/store82.sv'):
    if b['sources'][n]!=bm['source']['sources'][n]:raise ValueError('executed driver/store binding')
   cmd('simulation',[a.build/'obj/Vshared106',a.input/'vectors.tsv',a.out/'actual.jsonl',a.stall,a.pilot]);m['build_manifest_sha256']=sha(a.build/'manifest.json');m['input_manifest_sha256']=sha(a.input/'manifest.json');m['status']='GATE_EXECUTED_NOT_RECEIVED'
 except Exception as e:m['error']=str(e);m['traceback']=traceback.format_exc();raise
 finally:
  m['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in a.out.iterdir()if q.is_file()and q.name!='manifest.json'];put(a.out/'manifest.json',m)
 print(m['status'])
if __name__=='__main__':main()
