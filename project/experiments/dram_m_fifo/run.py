#!/usr/bin/env python3
"""Standalone Linux/Slurm runner; writes only inside a NEW --out directory."""
import argparse,concurrent.futures,hashlib,json,os,platform,shutil,subprocess,time
from pathlib import Path
def digest(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--verilator',required=True)
 ap.add_argument('--jobs',type=int,default=8);args=ap.parse_args()
 out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
 root=Path(__file__).resolve().parents[3]
 env=os.environ.copy();env.update(TMPDIR=str(out/'tmp'),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1')
 (out/'tmp').mkdir()
 rtl=[root/'project/rtl/dram_m_fifo/dm_async_fifo.sv',
 root/'project/rtl/dram_m_fifo/dram_m_fifo_loader.sv',
 root/'project/rtl/block_v2/block_v2_m.sv',Path(__file__).with_name('dram_m_fifo_tb.sv')]
 cpp=Path(__file__).with_name('test_direct.cpp')
 manifest={'schema':1,'started_unix':time.time(),'host':platform.node(),
 'slurm_job_id':os.getenv('SLURM_JOB_ID'),'slurm_cpus':os.getenv('SLURM_CPUS_PER_TASK'),
 'source':[digest(p) for p in rtl+[cpp,Path(__file__)]],
 'verilator':subprocess.check_output([args.verilator,'--version'],text=True).strip(),
 'g++':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
 'scope':'read-only controller user transaction model; actual unchanged M RTL; not DDR/PHY or physical CDC'}
 (out/'inputs.json').write_text(json.dumps(manifest,indent=2)+'\n')
 def invoke(cmd,log,**kw):
  start=time.time()
  with log.open('w') as f:
   p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,**kw)
  return {'argv':[str(x) for x in cmd],'returncode':p.returncode,'seconds':time.time()-start,'log':digest(log)}
 def build(depth):
  obj=out/f'obj-{depth}'
  cmd=[args.verilator,'--cc','--exe','--build','-j',str(max(1,args.jobs//2)),
   '--top-module','dram_m_fifo_tb',f'-GFIFO_DEPTH={depth}',
   '--Mdir',str(obj),'-Wno-fatal','--x-initial','unique','--x-assign','unique',
   '-CFLAGS','-std=c++17 -O2',*[str(x) for x in rtl],str(cpp)]
  rec=invoke(cmd,out/f'build-{depth}.log')
  rec['depth']=depth;rec['executable']=str(obj/'Vdram_m_fifo_tb')
  if rec['returncode']:raise RuntimeError(f'build-{depth} failed; see log')
  rec['binary']=digest(Path(rec['executable']))
  return rec
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  builds=list(pool.map(build,[2,16]))
 (out/'builds.json').write_text(json.dumps(builds,indent=2)+'\n')
 tasks=[(b,mh,mode) for b in builds for mh in [6,10,15] for mode in [0,1,2]]
 def run(task):
  b,mh,mode=task;seed=17300+mh*10+mode;phase=[0,3,7][mode]
  name=f"depth{b['depth']}-mh{mh}-init{mode}"
  cmd=[b['executable'],str(seed),str(mh),str(phase),
   f'+verilator+seed+{seed}',f'+verilator+rand+reset+{mode}']
  r=invoke(cmd,out/(name+'.log'));r.update(name=name,depth=b['depth'],initialization=mode)
  if r['returncode']==0:
   lines=Path(r['log']['path']).read_text().splitlines()
   r['result']=json.loads(next(x for x in reversed(lines) if x.startswith('{')))
  return r
 with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
  results=list(pool.map(run,tasks))
 negatives=[]
 for b in builds:
  cmd=[b['executable'],'173','6','3','corrupt','+verilator+rand+reset+2','+verilator+seed+173']
  r=invoke(cmd,out/f"negative-depth{b['depth']}.log")
  text=Path(r['log']['path']).read_text()
  r.update(depth=b['depth'],expected_failure=True,rejected=r['returncode']!=0 and 'B payload' in text)
  negatives.append(r)
 passed=all(r['returncode']==0 and r.get('result',{}).get('passed') for r in results) and all(r['rejected'] for r in negatives)
 report={'passed':passed,'schema':1,'host':platform.node(),'slurm_job_id':os.getenv('SLURM_JOB_ID'),
 'runs':results,'negative_controls':negatives,
 'summary':{'runs':len(results),'matrix_cases':sum(r.get('result',{}).get('matrix_cases',0) for r in results),
 'checks':sum(r.get('result',{}).get('checks',0) for r in results)},
 'time_unit':'one quantum=1/6ns; core half=10 =>300MHz; mem half6/10/15=>500/300/200MHz',
 'finished_unix':time.time()}
 (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'passed':passed,**report['summary'],'host':report['host'],'job':report['slurm_job_id']}))
 return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
