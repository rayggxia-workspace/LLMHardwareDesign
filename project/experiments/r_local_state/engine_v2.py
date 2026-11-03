"""Four builds, then all independent RTL cases in six dynamically refilled16CPU slots."""
from pathlib import Path
import os,subprocess,json,concurrent.futures,hashlib,queue,argparse,struct
p=argparse.ArgumentParser();p.add_argument('--finalize-pipeline-1024',action='store_true');p.add_argument('--baseline',type=Path);p.add_argument('--runtime-threads',type=int,choices=[1,16],default=16);a=p.parse_args()
ROOT=Path.cwd();P=ROOT/'project/experiments/r_local_state';S=ROOT/'project/rtl/r_local_state'
if a.finalize_pipeline_1024:S=P/'experimental_finalize'
C=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt003/results/corpus');M=json.loads((C/'MANIFEST.json').read_text());assert len(M['cases'])==63
cpus=sorted(os.sched_getaffinity(0));assert len(cpus)==96
slots=queue.Queue();[slots.put(cpus[i*16:(i+1)*16])for i in range(6)]
os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator';V='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source={str(p.relative_to(ROOT)):sha(p)for p in S.glob('*.sv')}
assert not a.baseline or a.finalize_pipeline_1024
baseline={};baseline_inputs={}
if a.baseline:
 assert sha(a.baseline.parent/'project/experiments/r_local_state/test_engine.cpp')==sha(P/'test_engine.cpp')
 assert sha(a.baseline.parent/'project/experiments/r_local_state/test_protocol.cpp')==sha(P/'test_protocol.cpp')
 for cap in [256,1024]:
  for init in range(3):
   path=a.baseline/str(cap)/f'init-{init}.json';row=json.loads(path.read_text());assert row['passed']and len(row['cases'])==63
   baseline[(cap,init)]=row;baseline_inputs[str(path)]=sha(path)

def launch(args,cwd,log):
 cores=slots.get()
 try:
  with log.open('w')as f:subprocess.run(['taskset','-c',','.join(map(str,cores))]+list(map(str,args)),cwd=cwd,stdout=f,stderr=subprocess.STDOUT,check=True)
 finally:slots.put(cores)

def build(item):
 cap,kind,test=item;out=ROOT/'results'/str(cap);out.mkdir(parents=True,exist_ok=True)
 launch([V,'--cc','--exe','--build','-j','16','--threads',str(a.runtime_threads),'-Wno-fatal','--top-module','r_stream_local','-GWORDS='+str(cap)]+(['-GFINALIZE_PIPELINE=1']if a.finalize_pipeline_1024 and cap==1024 else[])+['-CFLAGS','-O1 -DTEST_WORDS='+str(cap),'--Mdir',out/kind,S/'r_state_store.sv',S/'r_stream_local.sv',P/test],out,out/(kind+'-build.log'))

def task(item):
 cap,init,n=item;out=ROOT/'results'/str(cap);row=dict(capacity=cap,initialization=init,case=n,passed=False)
 try:
  args=['+verilator+rand+reset+'+str(init),'+verilator+seed+'+str(166+init)];kind='protocol'if n<0 else'engine';log=out/(f'protocol-{init}.log'if n<0 else f'test-{init}-{n}.log')
  inputs=[]
  if n>=0:
   case=M['cases'][n];inp=C/case['path'];assert sha(inp)==case['sha256'];inputs=[inp]
  launch([out/kind/'Vr_stream_local']+inputs+args,out,log);result=json.loads(log.read_text().strip());assert result['passed']is True
  if n>=0:assert result['words']==cap
  row.update(passed=True,result=result,log_sha256=sha(log))
  if a.baseline:
   if n<0:
    path=a.baseline/str(cap)/f'protocol-{init}.log';old=json.loads(path.read_text());assert result==old;row['baseline_sha256']=sha(path)
   else:
    old=baseline[(cap,init)]['cases'][n];assert old['case']==case['path']and old['input_sha256']==case['sha256']
    h=struct.unpack('<8I',inp.read_bytes()[:32]);extra=h[2]*h[3]*(2 if h[0]==0 else 1)if a.finalize_pipeline_1024 and cap==1024 else 0
    assert {k:v for k,v in result.items()if k!='cycles'}=={k:v for k,v in old['result'].items()if k!='cycles'}
    assert result['cycles']==old['result']['cycles']+extra,(item,result['cycles'],old['result']['cycles'],extra)
    row['expected_extra_cycles']=extra
 except Exception as e:row.update(passed=False,error=repr(e))
 return row

with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:
 list(pool.map(build,[(cap,kind,test)for cap in [256,1024]for kind,test in [('engine','test_engine.cpp'),('protocol','test_protocol.cpp')]]))
if a.runtime_threads==1:
 # Compilation still uses16 cores/build. Runtime cases are independent:
 # use96 single-core slots rather than reserve16 cores for one serial model.
 while not slots.empty():slots.get_nowait()
 for core in cpus:slots.put([core])
items=[(cap,init,n)for cap in [256,1024]for init in range(3)for n in range(-1,63)]
def cost(item):
 cap,init,n=item
 if n<0:return 10**18
 h=struct.unpack('<8I',(C/M['cases'][n]['path']).read_bytes()[:32]);return h[1]*h[2]*h[3]*cap
with concurrent.futures.ThreadPoolExecutor(max_workers=96//a.runtime_threads)as pool:
 results=list(pool.map(task,sorted(items,key=cost,reverse=True)))
for cap in [256,1024]:
 rows=[]
 for init in range(3):
  selected=sorted([r for r in results if r['capacity']==cap and r['initialization']==init],key=lambda r:r['case']);assert len(selected)==64 and {r['case']for r in selected}==set(range(-1,63))
  rec=dict(passed=all(r['passed']for r in selected),capacity=cap,init=init,source_sha256=source,finalize_pipeline=int(a.finalize_pipeline_1024 and cap==1024),simulation_threads=a.runtime_threads,baseline_inputs=baseline_inputs,cases=[dict(case=M['cases'][r['case']]['path'],input_sha256=M['cases'][r['case']]['sha256'],result=r.get('result'),passed=r['passed'],error=r.get('error'),expected_extra_cycles=r.get('expected_extra_cycles'))for r in selected if r['case']>=0],tasks=selected)
  (ROOT/'results'/str(cap)/f'init-{init}.json').write_text(json.dumps(rec,indent=2)+'\n');rows.append(rec)
 (ROOT/'results'/str(cap)/'receipt.json').write_text(json.dumps(dict(passed=all(r['passed']for r in rows),source_sha256=source,initializations=rows),indent=2)+'\n')
assert len(results)==384 and all(r['passed']for r in results)
