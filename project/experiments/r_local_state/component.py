from pathlib import Path
import concurrent.futures,subprocess,json,os,hashlib
ROOT=Path.cwd(); P=ROOT/'project/experiments/r_local_state'; RTL=ROOT/'project/rtl/r_local_state/r_state_store.sv'
cpus=sorted(os.sched_getaffinity(0)); assert len(cpus)>=32
os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
V='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
def run(cap,slot):
 out=ROOT/'results'/str(cap);out.mkdir(parents=True,exist_ok=False)
 prefix=['taskset','-c',','.join(map(str,cpus[slot*16:(slot+1)*16]))]
 def cmd(args,name):
  with(out/name).open('w')as f:subprocess.run(prefix+list(map(str,args)),cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
 result={'words':cap,'passed':False,'rtl_sha256':hashlib.sha256(RTL.read_bytes()).hexdigest()}
 try:
  cmd([V,'--cc','--exe','--build','-j','16','-Wno-fatal','--top-module','r_state_store','-GWORDS='+str(cap),'-CFLAGS','-O1 -DWORDS='+str(cap),'--Mdir',out/'obj',RTL,P/'test_store.cpp'],'build.log')
  for init,seed in [(0,166),(1,166),(2,167)]:cmd([out/'obj/Vr_state_store','+verilator+rand+reset+'+str(init),'+verilator+seed+'+str(seed)],'test-'+str(init)+'.log')
  result['passed']=True
 except Exception as e:result['error']=str(e)
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(lambda x:run(*x),[(256,0),(1024,1)]))
(ROOT/'results/receipt.json').write_text(json.dumps(results,indent=2)+'\n');assert all(x['passed']for x in results)
