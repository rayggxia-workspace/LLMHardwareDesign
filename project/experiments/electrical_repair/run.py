"""Issue86 server-only gate replay and explicitly cut logic timing."""
import argparse,hashlib,json,subprocess,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
R84=Path('/public/home/yuzelu/RuizhiLiang/issue84-cache-share-20261025')
LIB=Path('/public/home/yuzelu/RuizhiLiang/issue80-block-circuit-20261025/nangate45-reference/NangateOpenCellLibrary_typical.lib')
EDA=Path('/public/home/yuzelu/opt/eda')
ORFS=EDA/'cache/bazel-repacked/0472cb7817e9c4d6e974e10cde266a63/external/bazel-orfs++orfs_repositories+docker_orfs/OpenROAD-flow-scripts'
STA=ORFS/'tools/install/OpenROAD/bin/sta'
PREFIX=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind',str(EDA)+':/eda:ro']
SIF=str(EDA/'containers/orfs-26Q1-repacked.sif')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def load(p):return json.loads(Path(p).read_text())
def main():
 p=argparse.ArgumentParser();p.add_argument('task',choices=['prepare','build','sim','sta']);p.add_argument('--repair',type=Path);p.add_argument('--variant',type=int,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--prepared',type=Path);p.add_argument('--build',type=Path);p.add_argument('--stall',type=int,default=0);a=p.parse_args();binding=load(ROOT/'binding.json')
 for n,h in binding['sources'].items():
  if sha(ROOT/n)!=h:raise ValueError('source SHA '+n)
 a.out.mkdir(parents=True,exist_ok=False);m={'status':'ERROR','source':binding,'task':a.task,'variant':a.variant,'stall':a.stall,'library_sha256':sha(LIB)}
 def cmd(name,argv,seconds=900):
  if str(argv[0])==str(STA):argv=[ORFS.parent/'lib64/ld-linux-x86-64.so.2','--library-path',ORFS.parent/'usr/lib/x86_64-linux-gnu',*argv]
  args=[*PREFIX,'--pwd',str(a.out),SIF,*map(str,argv)];start=time.monotonic()
  with (a.out/(name+'.log')).open('w')as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=seconds)
  put(a.out/(name+'-command.json'),{'argv':args,'exit':r.returncode,'seconds':time.monotonic()-start})
  if r.returncode:raise ValueError('failed '+name)
 try:
  if a.task=='prepare':
   import re
   old=Path('/public/home/yuzelu/RuizhiLiang/issue86-gate-sta-20261025')/f'prepare-v{a.variant}01'
   rm=load(a.repair/'manifest.json');om=load(old/'manifest.json')
   if rm['status']!='REPAIR_EXECUTED_NOT_RECEIVED'or rm['variant']!=a.variant:raise ValueError('repair status/variant')
   for folder,manifest in((a.repair,rm),(old,om)):
    for e in manifest['artifacts']:
     if sha(folder/e['path'])!=e['sha256']:raise ValueError('source artifact SHA')
   original=load(old/'mapped.json')['modules']['chain84'];cut_contract=load(old/'cut-contract.json');new_raw=(a.repair/'repaired.v').read_text()
   core,n=re.subn(r'\bmodule chain84\b','module repaired_core',new_raw,count=1)
   if n!=1:raise ValueError('exact repaired top')
   decl=[];ports=[]
   for name,p in original['ports'].items():
    width=len(p['bits']);decl.append(p['direction']+' wire '+('['+str(width-1)+':0] 'if width>1 else'')+name);ports.append(name)
   extra=cut_contract['cut_ports'];internals=['wire '+('['+str(e['width']-1)+':0] 'if e['width']>1 else'')+e['port']+';'for e in extra]
   connections=','.join('.'+name+'('+name+')'for name in ports+[e['port']for e in extra]);bank=','.join('.'+e['port'][6:]+'('+e['port']+')'for e in extra)
   wrapper='module chain84('+','.join(decl)+');\n'+'\n'.join(internals)+'\nrepaired_core core('+connections+');\nstore82 memory(.clk(clk),.reset(reset),'+bank+');\nendmodule\n'
   (a.out/'mapped.v').write_text(core+'\n'+wrapper);(a.out/'cells.v').write_bytes((old/'cells.v').read_bytes());(a.out/'cut.v').write_text(new_raw);put(a.out/'cut-contract.json',cut_contract)
   script=f'read_liberty -lib {LIB}\nread_verilog {a.out}/cut.v\nhierarchy -top chain84\ncheck -assert\nwrite_json {a.out}/cut.json\ntee -o {a.out}/stat.json stat -liberty {LIB} -json\n'
   (a.out/'parse.ys').write_text(script);cmd('parse',['yosys','-s',a.out/'parse.ys']);m['repair_manifest_sha256']=sha(a.repair/'manifest.json');m['repair_directory']=str(a.repair);m['prior_prepared_manifest_sha256']=sha(old/'manifest.json');m['status']='EXACT_MAPPED_NETLIST_EXPORTED_WITH_DECLARED_STORE_CUT'
  elif a.task=='build':
   prep=load(a.prepared/'manifest.json')
   if prep['variant']!=a.variant or prep['status']!='EXACT_MAPPED_NETLIST_EXPORTED_WITH_DECLARED_STORE_CUT':raise ValueError('prepared variant/status')
   for e in prep['artifacts']:
    if sha(a.prepared/e['path'])!=e['sha256']:raise ValueError('prepared artifact')
   cmd('compile',['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','4','-Wno-fatal','--top-module','chain84','--prefix','Vchain84','--Mdir',a.out/'obj','--output-split','15000','--output-split-cfuncs','200','-CFLAGS',f'-std=c++17 -O2 -DCACHE_MODE={a.variant//2}',a.prepared/'mapped.v',a.prepared/'cells.v',ROOT/'project/rtl/norm_service/store82.sv',ROOT/'project/experiments/cache_share/chain_sim.cpp'],1500)
   m['prepared_manifest_sha256']=sha(a.prepared/'manifest.json');m['binary_sha256']=sha(a.out/'obj/Vchain84');m['status']='GATE_BINARY_BUILT_NOT_EXECUTED'
  elif a.task=='sim':
   bm=load(a.build/'manifest.json')
   if bm['variant']!=a.variant or bm['status']!='GATE_BINARY_BUILT_NOT_EXECUTED' or sha(a.build/'obj/Vchain84')!=bm['binary_sha256']:raise ValueError('binary SHA')
   src=R84/'input01'/f'vectors-c{a.variant//2}.tsv'
   (a.out/'vectors.tsv').write_text(src.read_text().splitlines()[0]+'\n');m['vectors_source_sha256']=sha(src)
   cmd('replay',[a.build/'obj/Vchain84',a.out/'vectors.tsv',a.out/'actual.jsonl',a.stall],1500)
   row=load_jsonl(a.out/'actual.jsonl')[0];gold=load_jsonl(R84/f'rtl-v{a.variant}s{a.stall}02'/'actual.jsonl')[0]
   if row!=gold:raise ValueError('mapped replay differs from original RTL row')
   proto=load(a.out/'actual.jsonl.protocol.json')
   if set(proto)!={'actual_M_active_reset','no_stale_completion','SRAM_retained'} or any(type(v) is not bool or not v for v in proto.values()):raise ValueError('protocol failed')
   m['baseline_output_sha256']=sha(R84/f'rtl-v{a.variant}s{a.stall}02'/'actual.jsonl');m['build_manifest_sha256']=sha(a.build/'manifest.json');m['row_name']=row['name'];m['cycles']=row['cycles'];m['status']='PASS_GATE_REPLAY_ALL_OBSERVABLES_AND_RESET'
  else:
   from timing import timing
   cmd('sta-version',[STA,'-version']);m['sta_loader_sha256']=sha(ORFS.parent/'lib64/ld-linux-x86-64.so.2');m['timing']=timing(a,cmd,STA,LIB,put,load,sha);m['status']='DECLARED_CUT_LOGIC_TIMING_EXECUTED'
 except Exception as e:m['error']=str(e);m['traceback']=traceback.format_exc();raise
 finally:
  m['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in a.out.iterdir()if q.is_file()and q.name!='manifest.json'];put(a.out/'manifest.json',m)
 print(m['status'])
def load_jsonl(p):return [json.loads(x)for x in Path(p).read_text().splitlines()if x.strip()]
if __name__=='__main__':main()