"""Server-only frozen build, RTL execution and generic synthesis."""
import argparse,hashlib,json,subprocess,time,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
RTL=ROOT/'project/rtl/wide_service'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def command(out,name,args,prefix,cwd=None):
 start=time.monotonic();r=subprocess.run([*prefix,*map(str,args)],cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (out/(name+'.log')).write_text(r.stdout,encoding='utf-8');record={'argv':[*prefix,*map(str,args)],'cwd':str(cwd),'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-start};put(out/(name+'-command.json'),record)
 if r.returncode:raise ValueError(name+' failed; original log preserved')
 return record
def main():
 p=argparse.ArgumentParser();p.add_argument('task',choices=['build','simulate','synth']);p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--mode',type=int,choices=[0,1],required=True);p.add_argument('--input',type=Path);p.add_argument('--build',type=Path);p.add_argument('--stall',type=int,choices=[0,1],default=0);p.add_argument('--limit',type=int,default=100000);p.add_argument('--prefix',default='[]');a=p.parse_args()
 binding=json.loads(a.binding.read_text())
 for name,digest in binding['sources'].items():
  if sha(ROOT/name)!=digest:raise ValueError('frozen exact source '+name)
 a.out.mkdir(parents=True,exist_ok=False);prefix=json.loads(a.prefix);m={'schema':'block-circuit-run80-v1','status':'ERROR','source':binding,'mode':a.mode,'stall':a.stall,'task':a.task};started=time.monotonic()
 sv=[RTL/n for n in('byte_alu.sv','ram128.sv','wide_engine.sv','memory_link.sv','wide_block.sv')]
 try:
  if a.task=='build':
   command(a.out,'version',['/eda/verilator-5.042/bin/verilator','--version'],prefix)
   command(a.out,'compile',['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','wide_block','--prefix','Vwide_block','-GLOCAL='+str(a.mode),'--Mdir',a.out/'build','-CFLAGS','-std=c++17 -O2',*sv,HERE/'sim.cpp'],prefix)
   m['binary']={'path':'build/Vwide_block','sha256':sha(a.out/'build/Vwide_block')};m['status']='BUILT_NOT_EXECUTED'
  elif a.task=='simulate':
   im=json.loads((a.input/'manifest.json').read_text());bm=json.loads((a.build/'manifest.json').read_text())
   if bm['status']!='BUILT_NOT_EXECUTED'or bm['mode']!=a.mode or sha(a.build/bm['binary']['path'])!=bm['binary']['sha256']:raise ValueError('exact built mode/binary')
   for path,digest in binding['sources'].items():
    if path.startswith('project/rtl/')or path.endswith('/sim.cpp'):
     if bm['source']['sources'].get(path)!=digest:raise ValueError('built RTL/testbench differs from frozen execution source')
   for entry in im['artifacts']:
    if sha(a.input/entry['path'])!=entry['sha256']:raise ValueError('exact input artifact')
   (a.out/'rom.hex').write_bytes((a.input/'rom.hex').read_bytes());m['input_manifest_sha256']=sha(a.input/'manifest.json');m['build_manifest_sha256']=sha(a.build/'manifest.json')
   command(a.out,'simulation',[a.build/bm['binary']['path'],a.input/'program.bin',a.input/'vectors.tsv',a.out/'actual.jsonl',str(a.stall),str(a.limit)],prefix,cwd=a.out)
   m['status']='RTL_EXECUTED'
  else:
   (a.out/'rom.hex').write_bytes((a.input/'rom.hex').read_bytes())
   script='read_verilog -sv '+' '.join(map(str,sv))+'\nhierarchy -top wide_block -chparam LOCAL '+str(a.mode)+'\nproc\nopt\nmemory_collect\nopt_clean\ncheck -assert\ntee -o '+str(a.out/'stat.json')+' stat -json\nwrite_json '+str(a.out/'netlist.json')+'\n'
   (a.out/'synth.ys').write_text(script,encoding='utf-8');command(a.out,'synthesis',['yosys','-s',a.out/'synth.ys'],prefix,cwd=a.out);m['status']='GENERIC_SYNTHESIZED_NOT_MACRO_OR_PPA'
   m['input_manifest_sha256']=sha(a.input/'manifest.json')
 except Exception as e:m['error']={'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()};raise
 finally:
  m['elapsed_seconds']=time.monotonic()-started;m['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in sorted(a.out.iterdir())if q.is_file()and q.name!='manifest.json'];put(a.out/'manifest.json',m)
 print(json.dumps({'status':m['status'],'out':str(a.out),'mode':a.mode}))
if __name__=='__main__':main()
