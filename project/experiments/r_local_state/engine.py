from pathlib import Path
import os,subprocess,json,concurrent.futures,hashlib
ROOT=Path.cwd();P=ROOT/'project/experiments/r_local_state';S=ROOT/'project/rtl/r_local_state'
C=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt003/results/corpus')
M=json.loads((C/'MANIFEST.json').read_text());cpus=sorted(os.sched_getaffinity(0));assert len(cpus)>=32
os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
V='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
def trial(cap,slot):
 out=ROOT/'results'/str(cap);out.mkdir(parents=True,exist_ok=False);result={'capacity':cap,'passed':False}
 prefix=['taskset','-c',','.join(map(str,cpus[slot*16:(slot+1)*16]))]
 def run(args,log):
  with(out/log).open('w')as f:subprocess.run(prefix+list(map(str,args)),cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
 try:
  run([V,'--cc','--exe','--build','-j','16','-Wno-fatal','--top-module','r_stream_local','-GWORDS='+str(cap),'-CFLAGS','-O1 -DTEST_WORDS='+str(cap),'--Mdir',out/'obj',S/'r_state_store.sv',S/'r_stream_local.sv',P/'test_engine.cpp'],'build.log')
  rows=[]
  for init,seed in [(0,166),(1,166),(2,167)]:
   for i,c in enumerate(M['cases']):
    inp=C/c['path'];assert hashlib.sha256(inp.read_bytes()).hexdigest()==c['sha256']
    log=f'test-{init}-{i}.log';run([out/'obj/Vr_stream_local',inp,'+verilator+rand+reset+'+str(init),'+verilator+seed+'+str(seed)],log)
    rows.append({'case':c['path'],'init':init,'input_sha256':c['sha256'],'log':log})
  result.update(passed=True,cases=rows)
 except Exception as e:result['error']=str(e)
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:rr=list(pool.map(lambda x:trial(*x),[(256,0),(1024,1)]))
(ROOT/'results/receipt.json').write_text(json.dumps(rr,indent=2)+'\n');assert all(x['passed']for x in rr)
