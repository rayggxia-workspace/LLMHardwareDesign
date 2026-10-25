"""Server Slurm build/simulation/map; explicit actual source and artifact binding."""
import argparse,hashlib,json,subprocess,time,traceback
from pathlib import Path
from contracts import CONTRACT
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',newline='\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('task',choices=['build','sim','map']);p.add_argument('--out',type=Path,required=True);p.add_argument('--input',type=Path);p.add_argument('--build',type=Path);p.add_argument('--stall',type=int,choices=[0,1],default=0);p.add_argument('--steps',type=int,default=1);p.add_argument('--first',type=int,default=0);p.add_argument('--mode',choices=['real','protocol','fixture','checkpoint'],default='real');p.add_argument('--library',type=Path);a=p.parse_args();bd=json.loads((ROOT/'binding.json').read_text())
 for n,h in bd['sources'].items():assert sha(ROOT/n)==h,n
 a.out.mkdir(parents=True,exist_ok=False);m={'contract':CONTRACT,'schema':'gdn104-run-v1','status':'ERROR','source':bd,'task':a.task,'stall':a.stall,'steps':a.steps,'first_slot':a.first,'mode':a.mode}
 prefix=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind','/public/home/yuzelu/opt/eda:/eda:ro','--pwd',str(a.out),'/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif']
 def cmd(name,args):
  argv=[*prefix,*map(str,args)];start=time.monotonic()
  with(a.out/(name+'.log')).open('w',newline='\n')as f:r=subprocess.run(argv,cwd=a.out,text=True,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=1800)
  put(a.out/(name+'-command.json'),{'argv':argv,'exit':r.returncode,'seconds':time.monotonic()-start})
  if r.returncode:raise ValueError('failed '+name)
 sv=[ROOT/'project/rtl/gdn_state/gdn104.sv',ROOT/'project/rtl/gdn_state/wide104.sv',ROOT/'project/rtl/runtime_cache/mul84.sv',ROOT/'project/rtl/norm_service/store82.sv',ROOT/'project/rtl/wide_service/memory_link.sv']
 try:
  if a.task=='build':
   cmd('build',['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','gdn104','--prefix','Vgdn104','--Mdir',a.out/'obj','-CFLAGS','-std=c++17 -O2',*sv,HERE/'gdn_sim.cpp']);m.update(status='BUILT_NOT_EXECUTED',binary_sha256=sha(a.out/'obj/Vgdn104'))
  elif a.task=='sim':
   b=json.loads((a.build/'manifest.json').read_text());im=json.loads((a.input/'manifest.json').read_text());assert b['status']=='BUILT_NOT_EXECUTED'and sha(a.build/'obj/Vgdn104')==b['binary_sha256']and im['status']=='VERIFIED_COEFFICIENTS_NOT_RTL'
   for n,h in bd['sources'].items():
    if n.startswith('project/rtl/')or n.endswith('/gdn_sim.cpp'):assert b['source']['sources'].get(n)==h,n
   for e in im['artifacts']:assert sha(a.input/e['path'])==e['sha256']and(a.input/e['path']).stat().st_size==e['bytes']
   m.update(input_manifest_sha256=sha(a.input/'manifest.json'),build_manifest_sha256=sha(a.build/'manifest.json'))
   cmd('sim',[a.build/'obj/Vgdn104',a.input/'image.bin',a.out,a.stall,a.steps,a.mode,a.first]);m['status']='RTL_EXECUTED_NOT_RECEIVED'
  else:
   g='read_verilog -sv '+' '.join(map(str,sv))+'\nhierarchy -top gdn104\nproc\nopt\nwreduce\nmemory_dff\nmemory_collect\nopt_clean\ncheck -assert\nwrite_json '+str(a.out/'generic.json')+'\n';(a.out/'generic.ys').write_text(g,newline='\n');cmd('generic',['yosys','-s',a.out/'generic.ys'])
   g='read_liberty -lib '+str(a.library)+'\nread_verilog -sv '+' '.join(map(str,sv))+'\nhierarchy -top gdn104\nblackbox store82\nsynth -top gdn104 -flatten -noabc\nabc -fast -exe /usr/local/bin/../bin/yosys-abc\nopt -fast\ndfflibmap -liberty '+str(a.library)+'\nabc -exe /usr/local/bin/../bin/yosys-abc -liberty '+str(a.library)+'\nclean\ncheck -assert\ntee -o '+str(a.out/'stat.json')+' stat -liberty '+str(a.library)+' -json\nwrite_json '+str(a.out/'mapped.json')+'\n';(a.out/'map.ys').write_text(g,newline='\n');cmd('map',['yosys','-s',a.out/'map.ys']);m.update(status='LOGIC_ONLY_MAPPED_NOT_PPA',top='gdn104',library_sha256=sha(a.library))
 except Exception as e:m.update(error=str(e),traceback=traceback.format_exc());raise
 finally:m['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in sorted(a.out.iterdir())if q.is_file()and q.name!='manifest.json'];put(a.out/'manifest.json',m)
 print(m['status'])
if __name__=='__main__':main()
