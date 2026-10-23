"""Issue-31 immutable, unlimited compute-node experiments."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
HOST = 'yuzelu@10.129.166.172'
IMAGE = '/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif'
p = argparse.ArgumentParser()
p.add_argument('attempt')
p.add_argument('--cores', type=int, default=1)
p.add_argument('--spec', type=Path)
a = p.parse_args()
assert a.attempt.replace('-', '').isalnum() and 0 < a.cores <= 64
remote = '/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-31/' + a.attempt
def ssh(cmd):
    return subprocess.check_output(['ssh', '-o', 'BatchMode=yes', HOST, cmd], text=True)
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=REPO, text=True).splitlines()
assert all('project/experiments/opentpu_h2/results/' in line for line in dirty), 'Commit runner first'
spec = json.loads(a.spec.read_text()) if a.spec else {'mode': 'inventory'}
spec.update(cores=a.cores, runner_commit=commit, remote=remote)
ssh('test ! -e ' + shlex.quote(remote) + ' && mkdir -p ' + shlex.quote(remote+'/runner'))
files = sorted(f for f in HERE.iterdir() if f.suffix in ('.py', '.tcl', '.sh'))
subprocess.run(['scp', *map(str, files), HOST+':'+remote+'/runner/'], check=True)
ssh('printf %s ' + shlex.quote(json.dumps(spec, indent=2)+'\n')+' > '+shlex.quote(remote+'/spec.json'))
ssh('bash -n '+shlex.quote(remote+'/runner/job.sh'))
job = ssh(shlex.join(['sbatch','--parsable','-p','c64','-N','1','-n','1','-c',str(a.cores),
    '--time=0','-J','yzl-h2-'+spec['mode'],'-o',remote+'/job.log','--chdir',remote,
    '--export=ALL,LLHD_IMAGE='+IMAGE,remote+'/runner/job.sh'])).strip()
readback = ssh('scontrol show job -o '+shlex.quote(job))
assert 'TimeLimit=UNLIMITED' in readback
receipt = dict(spec=spec,job_id=job,scheduler_readback=readback,host=HOST,image=IMAGE,
    submitted_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    runner_files={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
(HERE/'results').mkdir(exist_ok=True)
(HERE/'results'/(a.attempt+'-submission.json')).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
