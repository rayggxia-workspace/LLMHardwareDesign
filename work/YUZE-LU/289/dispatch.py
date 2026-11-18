"""Run independent, frozen commands inside one Slurm node allocation."""
import argparse,concurrent.futures,hashlib,json,os,pathlib,subprocess,time
p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('--slots',type=int,default=6);p.add_argument('--cpus',type=int,default=8);a=p.parse_args()
assert 1<=a.slots<=8 and a.cpus>0
assert a.slots*a.cpus<=int(os.environ['SLURM_CPUS_ON_NODE'])
manifest=pathlib.Path(a.manifest).resolve();tasks=json.loads(manifest.read_text())
assert len({t['name'] for t in tasks})==len(tasks)
receipt=manifest.with_name('dispatch-'+os.environ['SLURM_JOB_ID']+'.json')
results=[]
def run(t):
 directory=pathlib.Path(t['cwd']);directory.mkdir(parents=True,exist_ok=True)
 log=directory/('dispatch-'+os.environ['SLURM_JOB_ID']+'.log')
 start=time.time()
 with log.open('x') as f:
  code=subprocess.call(['srun','--exclusive','-N1','-n1','-c',str(a.cpus),'--cpu-bind=cores',*t['argv']],cwd=directory,stdout=f,stderr=subprocess.STDOUT)
 return dict(name=t['name'],argv=t['argv'],cwd=str(directory),returncode=code,elapsed_seconds=time.time()-start,log=str(log))
with concurrent.futures.ThreadPoolExecutor(max_workers=a.slots) as executor:
 for result in executor.map(run,tasks):
  results.append(result)
  receipt.write_text(json.dumps(dict(job=os.environ['SLURM_JOB_ID'],manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),slots=a.slots,cpus=a.cpus,results=results),indent=2))
raise SystemExit(0 if all(r['returncode']==0 for r in results) else 1)
