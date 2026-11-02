"""Independent arithmetic and protocol scoreboards on exact mapped/final cells."""
from pathlib import Path
import os,subprocess,json,hashlib,argparse,concurrent.futures,queue
p=argparse.ArgumentParser();p.add_argument('--capacity',type=int,choices=[256,1024],required=True);p.add_argument('--netlist',type=Path,required=True);p.add_argument('--build-only',action='store_true');p.add_argument('--threads',type=int,choices=[1,16],default=1);a=p.parse_args()
R=Path.cwd();P=Path(__file__).resolve().parent;O=R/'netlist-test';O.mkdir(exist_ok=False)
L=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
C=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt003/results/corpus');M=json.loads((C/'MANIFEST.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs={str(f):sha(f)for f in [a.netlist,L,P/'test_engine.cpp',P/'test_protocol.cpp',C/'MANIFEST.json']}
(O/'BUILD_BINDING.json').write_text(json.dumps({'capacity':a.capacity,'inputs':inputs,'script_sha256':sha(Path(__file__)),'simulation_threads':a.threads},indent=2)+'\n')
cores=sorted(os.sched_getaffinity(0));assert len(cores)>=(32 if a.build_only else 48)
slots=queue.Queue();[slots.put(cores[i*16:(i+1)*16])for i in range(min(3,len(cores)//16))]
os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
V='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
def run(args,log):
 cc=slots.get()
 try:
  with log.open('w')as f:subprocess.run(['taskset','-c',','.join(map(str,cc))]+list(map(str,args)),cwd=O,stdout=f,stderr=subprocess.STDOUT,check=True)
 finally:slots.put(cc)
(O/'cells.ys').write_text('read_liberty -ignore_miss_func -ignore_miss_dir '+str(L)+'\nwrite_verilog -noattr cells.v\n')
run(['yosys','-s','cells.ys'],O/'cells.log')
def build(kind):
 run([V,'--cc','--exe','--build','-j','16','--threads',str(a.threads),'--x-initial','unique','--x-assign','unique','-Wno-fatal','--top-module','r_stream_local','--output-split','12000','--output-split-cfuncs','150','-CFLAGS','-O1 -DTEST_WORDS='+str(a.capacity),'--Mdir',O/kind,a.netlist,O/'cells.v',P/('test_'+kind+'.cpp')],O/(kind+'-build.log'))
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(build,['engine','protocol']))
if a.build_only:
 (O/'BUILD_COMPLETE.json').write_text(json.dumps({'inputs':inputs,'binaries':{k:sha(O/k/'Vr_stream_local')for k in ['engine','protocol']},'passed':True,'simulation_threads':a.threads},indent=2)+'\n');raise SystemExit(0)
def test(i):
 rec={'passed':False,'initialization':i,'cases':[]}
 try:
  args=['+verilator+rand+reset+'+str(i),'+verilator+seed+'+str(166+i)]
  run([O/'protocol/Vr_stream_local']+args,O/f'protocol-{i}.log')
  rec['protocol']=json.loads((O/f'protocol-{i}.log').read_text().strip())
  for n,c in enumerate(M['cases']):
   inp=C/c['path'];assert sha(inp)==c['sha256'];log=O/f'case-{i}-{n}.log'
   run([O/'engine/Vr_stream_local',inp]+args,log)
   rec['cases'].append({'input':c,'scoreboard':json.loads(log.read_text().strip())})
  rec['passed']=True
 except Exception as e:rec['error']=str(e)
 (O/f'init-{i}.json').write_text(json.dumps(rec,indent=2)+'\n');return rec
with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:rows=list(pool.map(test,range(3)))
assert inputs=={f:sha(Path(f))for f in inputs}
(O/'receipt.json').write_text(json.dumps({'passed':all(r['passed']for r in rows),'capacity':a.capacity,'inputs':inputs,'cell_models_sha256':sha(O/'cells.v'),'initializations':rows,'scope':'Exact provided netlist with Liberty-derived cell behavior; no RAM substitution. Zero-delay functionality only, separate from physical qualification.'},indent=2)+'\n')
assert all(r['passed']for r in rows)
