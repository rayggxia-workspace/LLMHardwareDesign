"""Read-only tool/environment receipt for the already installed server toolchain."""
import argparse,hashlib,json,os,platform,shutil,subprocess,time
from pathlib import Path
from probe import ROOT,EDA,DOCKER,ORFS,OR,STA,LIB,TECH,LEF

def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);binding=json.loads((ROOT/'binding.json').read_text())
 for n,h in binding['sources'].items():
  if sha(ROOT/n)!=h:raise ValueError('environment source SHA')
 sif=EDA/'containers/orfs-26Q1-repacked.sif';prefix=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind',str(EDA)+':/eda:ro','--pwd',str(a.out),str(sif)];loader=[str(DOCKER/'lib64/ld-linux-x86-64.so.2'),'--library-path',str(DOCKER/'usr/lib/x86_64-linux-gnu')]
 commands=[]
 for n,argv in [('yosys',['yosys','-V']),('verilator',['/eda/verilator-5.042/bin/verilator','--version']),('openroad',[*loader,str(OR),'-version']),('opensta',[*loader,str(STA),'-version'])]:
  r=subprocess.run([*prefix,*argv],capture_output=True,text=True,timeout=90);(a.out/(n+'.log')).write_text(r.stdout+r.stderr);commands.append({'tool':n,'argv':[*prefix,*argv],'exit':r.returncode,'log_sha256':sha(a.out/(n+'.log'))})
  if r.returncode:raise ValueError('tool version command '+n)
 files=[sif,LIB,TECH,LEF,OR,STA,DOCKER/'lib64/ld-linux-x86-64.so.2'];data={'status':'PASS_INSTALLED_TOOLCHAIN_READONLY_RECEIPT','source':binding,'files':[{'path':str(q),'bytes':q.stat().st_size,'sha256':sha(q)}for q in files],'commands':commands,'platform':platform.platform(),'hostname':platform.node(),'python':platform.python_version(),'cpuset':sorted(os.sched_getaffinity(0)),'loadavg':list(os.getloadavg()),'disk':dict(zip(('total','used','free'),shutil.disk_usage(a.out))),'slurm':{n:os.environ.get(n)for n in('SLURM_JOB_ID','SLURM_JOB_NAME','SLURM_JOB_NODELIST','SLURM_CPUS_PER_TASK')},'meminfo':Path('/proc/meminfo').read_text(),'scope':'Existing installed tools and read-only files only; parallel wall times are execution records, not isolated hardware performance.'}
 (a.out/'receipt.json').write_text(json.dumps(data,indent=2)+'\n');print(data['status'])
if __name__=='__main__':main()