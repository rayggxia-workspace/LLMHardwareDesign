import hashlib,json,os,shlex,subprocess,zipfile
from pathlib import Path
REPO=Path('D:/Projects/LLMHardwareDesign-scale-state')
TEMP=Path('D:/Projects/Codex/issue66-scale-state-20261024')
REMOTE='/public/home/yuzelu/RuizhiLiang/issue66-scale-state-20261024'
PREV='/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023'
PYTHON=PREV+'/venv-modern/bin/python'
SSH=['C:/Windows/System32/OpenSSH/ssh.exe','-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1','-i','C:/Users/23123/.ssh/id_ed25519_liangruizhi_lab_20261020','yuzelu@10.129.166.172']
SCP=['C:/Windows/System32/OpenSSH/scp.exe',*SSH[1:-1]]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n',newline='\n')
def remote(script,name):
 for attempt in range(3):
  r=subprocess.run([*SSH,'bash -s'],input=script.encode('utf-8'),capture_output=True,timeout=45)
  r.stdout=r.stdout.decode('utf-8');r.stderr=r.stderr.decode('utf-8')
  if r.returncode==0 or not ('connect to host' in r.stderr and 'timed out' in r.stderr):break
  (TEMP/(name+'-connect-failure'+str(attempt)+'.log')).write_text(r.stderr,newline='\n')
 (TEMP/(name+'.log')).write_text(r.stdout+r.stderr,newline='\n')
 if r.returncode:raise RuntimeError(name+': '+r.stderr[-1000:])
 return r.stdout.strip()
def stage(phase,paths,extra=None):
 if not REMOTE.startswith('/public/home/yuzelu/RuizhiLiang/')or'..'in Path(REMOTE).parts:raise ValueError('root')
 if subprocess.check_output(['git','status','--porcelain'],cwd=REPO):raise ValueError('dirty source')
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
 b={'commit':commit,'sources':{p:sha(REPO/p)for p in paths},**(extra or{})}
 archive=TEMP/(phase+'-source.zip');save(TEMP/(phase+'-binding.json'),b)
 with zipfile.ZipFile(archive,'x')as z:
  for p in paths:z.write(REPO/p,p)
  z.write(TEMP/(phase+'-binding.json'),'binding.json')
 remote('set -eu\numask 077\nmkdir -p '+shlex.quote(REMOTE+'/tmp')+'\ntest ! -e '+shlex.quote(REMOTE+'/'+phase)+'\nmkdir '+shlex.quote(REMOTE+'/'+phase)+'\n',phase+'-prepare')
 subprocess.run([*SCP,str(archive),'yuzelu@10.129.166.172:'+REMOTE+'/'+phase+'/source.zip'],check=True,timeout=60,capture_output=True)
 remote('set -eu\ncd '+shlex.quote(REMOTE+'/'+phase)+'\nprintf '+shlex.quote(sha(archive)+'  source.zip\n')+' | sha256sum -c -\n'+shlex.quote(PYTHON)+' -m zipfile -e source.zip .\n',phase+'-extract')
 save(TEMP/(phase+'-staging.json'),{'commit':commit,'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'binding':b})
 return b
def submit(tag,phase,entry,args,cpus=2,minutes=20,depends=None):
 cmd=[PYTHON,'-u','-B',REMOTE+'/'+phase+'/'+entry,*args]
 wrap=' '.join(shlex.quote(str(v))for v in cmd)
 slurm=['sbatch','--parsable','--job-name=lrz-i66-'+tag,'--partition=c96','--cpus-per-task='+str(cpus),'--time=00:'+str(minutes).zfill(2)+':00','--output='+REMOTE+'/'+tag+'-%j.log']
 if depends:slurm+=['--dependency=afterok:'+':'.join(map(str,depends))]
 slurm+=['--wrap',wrap]
 script='set -eu\ncd '+shlex.quote(REMOTE)+'\nexport TMPDIR='+shlex.quote(REMOTE+'/tmp')+' PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1\n'+' '.join(shlex.quote(v)for v in slurm)+'\n'
 result=remote(script,tag+'-submit');save(TEMP/(tag+'-submit.json'),{'command':cmd,'wrap':wrap,'slurm_argv':slurm,'stdout':result,'phase':phase,'binding_sha256':sha(TEMP/(phase+'-binding.json'))});print(json.dumps({'tag':tag,'job':result}),flush=True)
 return result
