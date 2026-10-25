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
 p=argparse.ArgumentParser();p.add_argument('task',choices=['prepare','build','sim','sta']);p.add_argument('--variant',type=int,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--prepared',type=Path);p.add_argument('--build',type=Path);p.add_argument('--stall',type=int,default=0);a=p.parse_args();binding=load(ROOT/'binding.json')
 for n,h in binding['sources'].items():
  if sha(ROOT/n)!=h:raise ValueError('source SHA '+n)
 a.out.mkdir(parents=True,exist_ok=False);m={'status':'ERROR','source':binding,'task':a.task,'variant':a.variant,'stall':a.stall,'library_sha256':sha(LIB)}
 def cmd(name,argv,seconds=900):
  args=[*PREFIX,'--pwd',str(a.out),SIF,*map(str,argv)];start=time.monotonic()
  with (a.out/(name+'.log')).open('w')as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=seconds)
  put(a.out/(name+'-command.json'),{'argv':args,'exit':r.returncode,'seconds':time.monotonic()-start})
  if r.returncode:raise ValueError('failed '+name)
 try:
  if a.task=='prepare':
   source=R84/f'map-v{a.variant}03';mm=load(source/'manifest.json')
   for e in mm['artifacts']:
    if sha(source/e['path'])!=e['sha256']:raise ValueError('prior map SHA')
   if mm['library_sha256']!=sha(LIB):raise ValueError('library mismatch')
   m['mapping_manifest_sha256']=sha(source/'manifest.json');m['mapping_source']=mm['source'];(a.out/'mapped.json').write_bytes((source/'mapped.json').read_bytes())
   script=f'read_json {a.out}/mapped.json\nwrite_verilog -noattr -noexpr {a.out}/mapped.v\ndesign -reset\nread_liberty -ignore_miss_func -ignore_miss_dir {LIB}\nwrite_verilog -noattr {a.out}/cells.v\n'
   (a.out/'export.ys').write_text(script);cmd('export',['yosys','-s',a.out/'export.ys'])
   data=load(source/'mapped.json');top=data['modules']['chain84'];stores=[(n,c)for n,c in top['cells'].items()if c['type']=='store82']
   if len(stores)!=1:raise ValueError('single store')
   name,store=stores[0];cut=[]
   for port,bits in store['connections'].items():
    if port in('clk','reset'):continue
    direction='input'if store['port_directions'][port]=='output'else'output';n='store_'+port
    top['ports'][n]={'direction':direction,'bits':bits};cut.append({'port':n,'direction':direction,'width':len(bits),'original':name+'.'+port})
   del top['cells'][name];data['modules'].pop('store82',None);put(a.out/'cut.json',data);put(a.out/'cut-contract.json',{'removed':name,'cut_ports':cut,'omitted_store_clock_and_reset':True,'meaning':'Behavioral store wrapper wholly excluded; logic-only interface cut, not SRAM timing.'})
   (a.out/'cut.ys').write_text(f'read_json {a.out}/cut.json\nwrite_verilog -noattr -noexpr {a.out}/cut.v\n');cmd('cut',['yosys','-s',a.out/'cut.ys']);cmd('versions',['bash','-c',f'yosys -V; {STA} -version; /eda/verilator-5.042/bin/verilator --version'])
   m['sta_binary_sha256']=sha(STA);m['status']='EXACT_MAPPED_NETLIST_EXPORTED_WITH_DECLARED_STORE_CUT'
  elif a.task=='build':
   prep=load(a.prepared/'manifest.json')
   for e in prep['artifacts']:
    if sha(a.prepared/e['path'])!=e['sha256']:raise ValueError('prepared artifact')
   cmd('compile',['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','4','-Wno-fatal','--top-module','chain84','--prefix','Vchain84','--Mdir',a.out/'obj','--output-split','15000','--output-split-cfuncs','200','-CFLAGS',f'-std=c++17 -O2 -DCACHE_MODE={a.variant//2}',a.prepared/'mapped.v',a.prepared/'cells.v',ROOT/'project/rtl/norm_service/store82.sv',ROOT/'project/experiments/cache_share/chain_sim.cpp'],1500)
   m['prepared_manifest_sha256']=sha(a.prepared/'manifest.json');m['binary_sha256']=sha(a.out/'obj/Vchain84');m['status']='GATE_BINARY_BUILT_NOT_EXECUTED'
  elif a.task=='sim':
   bm=load(a.build/'manifest.json')
   if sha(a.build/'obj/Vchain84')!=bm['binary_sha256']:raise ValueError('binary SHA')
   src=R84/'input01'/f'vectors-c{a.variant//2}.tsv'
   (a.out/'vectors.tsv').write_text(src.read_text().splitlines()[0]+'\n');m['vectors_source_sha256']=sha(src)
   cmd('replay',[a.build/'obj/Vchain84',a.out/'vectors.tsv',a.out/'actual.jsonl',a.stall],1500)
   row=load_jsonl(a.out/'actual.jsonl')[0];gold=load_jsonl(R84/f'rtl-v{a.variant}s{a.stall}02'/'actual.jsonl')[0]
   if row!=gold:raise ValueError('mapped replay differs from original RTL row')
   proto=load(a.out/'actual.jsonl.protocol.json')
   if not all(proto.values()):raise ValueError('protocol failed')
   m['baseline_output_sha256']=sha(R84/f'rtl-v{a.variant}s{a.stall}02'/'actual.jsonl');m['build_manifest_sha256']=sha(a.build/'manifest.json');m['row_name']=row['name'];m['cycles']=row['cycles'];m['status']='PASS_GATE_REPLAY_ALL_OBSERVABLES_AND_RESET'
  else:
   from timing import timing
   m['timing']=timing(a,cmd,STA,LIB,put,load,sha);m['status']='DECLARED_CUT_LOGIC_TIMING_EXECUTED'
 except Exception as e:m['error']=str(e);m['traceback']=traceback.format_exc();raise
 finally:
  m['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)}for q in a.out.iterdir()if q.is_file()and q.name!='manifest.json'];put(a.out/'manifest.json',m)
 print(m['status'])
def load_jsonl(p):return [json.loads(x)for x in Path(p).read_text().splitlines()if x.strip()]
if __name__=='__main__':main()