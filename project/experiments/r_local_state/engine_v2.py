"""Two builds, then six independent initialization tasks with dynamic slot refill."""
from pathlib import Path
import os,subprocess,json,concurrent.futures,hashlib,threading,queue
ROOT=Path.cwd();P=ROOT/'project/experiments/r_local_state';S=ROOT/'project/rtl/r_local_state'
C=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt003/results/corpus');M=json.loads((C/'MANIFEST.json').read_text())
cpus=sorted(os.sched_getaffinity(0));assert len(cpus)>=96
slots=queue.Queue();[slots.put(cpus[i*16:(i+1)*16])for i in range(6)]
os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator';V='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
source={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in S.glob('*.sv')}
def launch(args,cwd,log):
 cores=slots.get()
 try:
  with log.open('w')as f:subprocess.run(['taskset','-c',','.join(map(str,cores))]+list(map(str,args)),cwd=cwd,stdout=f,stderr=subprocess.STDOUT,check=True)
 finally:slots.put(cores)
def build(cap):
 out=ROOT/'results'/str(cap);out.mkdir(parents=True,exist_ok=False)
 for kind,test in [('engine','test_engine.cpp'),('protocol','test_protocol.cpp')]:
  launch([V,'--cc','--exe','--build','-j','16','-Wno-fatal','--top-module','r_stream_local','-GWORDS='+str(cap),'-CFLAGS','-O1 -DTEST_WORDS='+str(cap),'--Mdir',out/kind,S/'r_state_store.sv',S/'r_stream_local.sv',P/test],out,out/(kind+'-build.log'))
 return cap
def task(cap,init):
 out=ROOT/'results'/str(cap);rec={'passed':False,'capacity':cap,'init':init,'source_sha256':source,'cases':[]}
 try:
  seed=166+init;args=['+verilator+rand+reset+'+str(init),'+verilator+seed+'+str(seed)]
  launch([out/'protocol/Vr_stream_local']+args,out,out/f'protocol-{init}.log')
  for i,c in enumerate(M['cases']):
   inp=C/c['path'];assert hashlib.sha256(inp.read_bytes()).hexdigest()==c['sha256']
   log=out/f'test-{init}-{i}.log';launch([out/'engine/Vr_stream_local',inp]+args,out,log)
   rec['cases'].append({'case':c['path'],'input_sha256':c['sha256'],'result':json.loads(log.read_text().strip())})
  rec['passed']=True
 except Exception as e:rec['error']=str(e)
 (out/f'init-{init}.json').write_text(json.dumps(rec,indent=2)+'\n');return rec
with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:
 list(pool.map(build,[256,1024]));results=list(pool.map(lambda x:task(*x),[(c,i)for c in [256,1024]for i in range(3)]))
for cap in [256,1024]:
 rows=[r for r in results if r['capacity']==cap]
 (ROOT/'results'/str(cap)/'receipt.json').write_text(json.dumps({'passed':all(r['passed']for r in rows),'source_sha256':source,'initializations':rows},indent=2)+'\n')
assert all(r['passed']for r in results)
