"""Frozen server-only build, execution and logic mapping."""
import argparse,hashlib,json,subprocess,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;RTL=ROOT/'project/rtl/cache_share'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('task',choices=['build','sim','map']);p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--profile',type=int,required=True);p.add_argument('--stall',type=int,default=0);p.add_argument('--input',type=Path);p.add_argument('--build',type=Path);p.add_argument('--prefix',required=True);p.add_argument('--library',type=Path);a=p.parse_args();bd=json.loads(a.binding.read_text())
 for n,h in bd['sources'].items():
  if sha(ROOT/n)!=h:raise ValueError('exact source '+n)
 a.out.mkdir(exist_ok=False,parents=True);m={'status':'ERROR','source':bd,'profile':a.profile,'stall':a.stall,'task':a.task};prefix=json.loads(a.prefix);prefix=prefix[:-1]+['--pwd',str(a.out),prefix[-1]]
 def cmd(name,args):
  start=time.monotonic();r=subprocess.run([*prefix,*map(str,args)],cwd=a.out,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(a.out/(name+'.log')).write_text(r.stdout);put(a.out/(name+'-command.json'),{'argv':[*prefix,*map(str,args)],'exit':r.returncode,'seconds':time.monotonic()-start})
  if r.returncode:raise ValueError('failed '+name)
 sv=[RTL/n for n in('sfu84.sv','mul84.sv','norm84.sv','mfront84.sv','chain84.sv')]+[ROOT/'project/rtl/wide_service/memory_link.sv',ROOT/'project/rtl/norm_service/store82.sv']
 try:
  if a.task=='build':
   cmd('build',['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','chain84','--prefix','Vchain84','-GCACHE='+str(a.profile//2),'-GSHARE='+str(a.profile%2),'--Mdir',a.out/'obj','-CFLAGS','-std=c++17 -O2 -DCACHE_MODE='+str(a.profile//2),*sv,HERE/'chain_sim.cpp']);m['binary_sha256']=sha(a.out/'obj/Vchain84');m['status']='BUILT_NOT_EXECUTED'
  elif a.task=='sim':
   b=json.loads((a.build/'manifest.json').read_text());im=json.loads((a.input/'manifest.json').read_text())
   if b['status']!='BUILT_NOT_EXECUTED'or b['profile']!=a.profile or sha(a.build/'obj/Vchain84')!=b['binary_sha256']:raise ValueError('exact build')
   for n,h in bd['sources'].items():
    if n.startswith('project/rtl/')or n.endswith('/chain_sim.cpp'):
     if b['source']['sources'].get(n)!=h:raise ValueError('build source mismatch')
   for e in im['artifacts']:
    if sha(a.input/e['path'])!=e['sha256']:raise ValueError('input SHA')
   cmd('simulation',[a.build/'obj/Vchain84',a.input/f'vectors-c{a.profile//2}.tsv',a.out/'actual.jsonl',a.stall]);m['input_manifest_sha256']=sha(a.input/'manifest.json');m['status']='RTL_EXECUTED_NOT_RECEIVED'
  else:
   script='read_verilog -sv '+' '.join(map(str,sv))+'\nhierarchy -top chain84 -chparam CACHE '+str(a.profile//2)+' -chparam SHARE '+str(a.profile%2)+'\nproc\nopt\nwreduce\nmemory_dff\nmemory_collect\nopt_clean\ncheck -assert\nwrite_json '+str(a.out/'generic.json')+'\n'
   (a.out/'generic.ys').write_text(script);cmd('generic',['yosys','-s',a.out/'generic.ys'])
   lib=a.library;script='read_liberty -lib '+str(lib)+'\nread_verilog -sv '+' '.join(map(str,sv))+'\nhierarchy -top chain84 -chparam CACHE '+str(a.profile//2)+' -chparam SHARE '+str(a.profile%2)+'\nblackbox store82\nsynth -top chain84 -flatten\ndfflibmap -liberty '+str(lib)+'\nabc -liberty '+str(lib)+'\nclean\ncheck -assert\ntee -o '+str(a.out/'stat.json')+' stat -liberty '+str(lib)+' -json\nwrite_json '+str(a.out/'mapped.json')+'\n'
   (a.out/'map.ys').write_text(script);cmd('map',['yosys','-s',a.out/'map.ys']);m['library_sha256']=sha(lib);m['status']='LOGIC_ONLY_MAPPED_NOT_PPA'
 except Exception as e:m['error']=str(e);m['traceback']=traceback.format_exc();raise
 finally:
  m['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in a.out.iterdir()if q.is_file()and q.name!='manifest.json'];put(a.out/'manifest.json',m)
 print(m['status'])
if __name__=='__main__':main()
