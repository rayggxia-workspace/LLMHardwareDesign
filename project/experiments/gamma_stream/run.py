"""Server-only exact source builds, RTL execution and logic-only maps."""
import argparse,hashlib,json,subprocess,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('task',choices=['build','sim','map']);p.add_argument('--out',type=Path,required=True);p.add_argument('--input',type=Path);p.add_argument('--build',type=Path);p.add_argument('--stall',type=int,choices=[0,1],default=0);p.add_argument('--baseline',action='store_true');p.add_argument('--library',type=Path);a=p.parse_args();bd=json.loads((ROOT/'binding.json').read_text())
 for n,h in bd['sources'].items():
  if sha(ROOT/n)!=h:raise ValueError('source SHA '+n)
 a.out.mkdir(parents=True,exist_ok=False);m={'status':'ERROR','schema':'gamma93-run-v1','source':bd,'task':a.task,'stall':a.stall,'baseline':a.baseline}
 prefix=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind','/public/home/yuzelu/opt/eda:/eda:ro','--pwd',str(a.out),'/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif']
 def cmd(name,args):
  argv=[*prefix,*map(str,args)];start=time.monotonic()
  with(a.out/(name+'.log')).open('w')as f:r=subprocess.run(argv,cwd=a.out,text=True,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=900)
  put(a.out/(name+'-command.json'),{'argv':argv,'exit':r.returncode,'seconds':time.monotonic()-start})
  if r.returncode:raise ValueError('failed '+name)
 old=ROOT/'project/rtl/runtime_cache';new=ROOT/'project/rtl/gamma_stream';top='chain85'if a.baseline else'chain93'
 sv=[old/n for n in('sfu84.sv','mul84.sv','mfront85.sv')]+([old/'norm84.sv',old/'chain85.sv']if a.baseline else[new/'norm93.sv',new/'chain93.sv'])+[ROOT/'project/rtl/norm_service/store82.sv',ROOT/'project/rtl/wide_service/memory_link.sv']
 try:
  if a.task=='build':
   if a.baseline:raise ValueError('baseline mapping only; old data functionality remains prior92')
   cmd('build',['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','2','-Wno-fatal','--top-module',top,'--prefix','Vchain93','--Mdir',a.out/'obj','-CFLAGS','-std=c++17 -O2',*sv,HERE/'chain_sim.cpp']);m.update(status='BUILT_NOT_EXECUTED',binary_sha256=sha(a.out/'obj/Vchain93'))
  elif a.task=='sim':
   b=json.loads((a.build/'manifest.json').read_text());im=json.loads((a.input/'manifest.json').read_text())
   if b['status']!='BUILT_NOT_EXECUTED'or b['baseline']or sha(a.build/'obj/Vchain93')!=b['binary_sha256']or im['status']!='PASS_VERIFIED_INPUTS_NOT_RTL':raise ValueError('actual build/input binding')
   for n,h in bd['sources'].items():
    if n.startswith('project/rtl/')or n.endswith('/chain_sim.cpp'):
     if b['source']['sources'].get(n)!=h:raise ValueError('executed source '+n)
   for e in im['artifacts']:
    if sha(a.input/e['path'])!=e['sha256']:raise ValueError('input artifacts '+e['path'])
   m.update(build_manifest_sha256=sha(a.build/'manifest.json'),input_manifest_sha256=sha(a.input/'manifest.json'));cmd('simulation',[a.build/'obj/Vchain93',a.input/'vectors93.tsv',a.out/'actual.jsonl',a.stall]);m['status']='RTL_EXECUTED_NOT_RECEIVED'
  else:
   script='read_verilog -sv '+' '.join(map(str,sv))+'\nhierarchy -top '+top+'\nproc\nopt\nwreduce\nmemory_dff\nmemory_collect\nopt_clean\ncheck -assert\nwrite_json '+str(a.out/'generic.json')+'\n';(a.out/'generic.ys').write_text(script);cmd('generic',['yosys','-s',a.out/'generic.ys'])
   script='read_liberty -lib '+str(a.library)+'\nread_verilog -sv '+' '.join(map(str,sv))+'\nhierarchy -top '+top+'\nblackbox store82\nsynth -top '+top+' -flatten -noabc\nabc -fast -exe /usr/local/bin/../bin/yosys-abc\nopt -fast\ndfflibmap -liberty '+str(a.library)+'\nabc -exe /usr/local/bin/../bin/yosys-abc -liberty '+str(a.library)+'\nclean\ncheck -assert\ntee -o '+str(a.out/'stat.json')+' stat -liberty '+str(a.library)+' -json\nwrite_json '+str(a.out/'mapped.json')+'\n';(a.out/'map.ys').write_text(script);cmd('map',['yosys','-s',a.out/'map.ys']);m.update(status='LOGIC_ONLY_MAPPED_NOT_PPA',library_sha256=sha(a.library),top=top)
 except Exception as e:m['error']=str(e);m['traceback']=traceback.format_exc();raise
 finally:m['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in sorted(a.out.iterdir())if q.is_file()and q.name!='manifest.json'];put(a.out/'manifest.json',m)
 print(m['status'])
if __name__=='__main__':main()
