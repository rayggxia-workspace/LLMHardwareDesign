from pathlib import Path
import subprocess,shlex,json
h=Path(__file__).parent;host='yuzelu@10.129.166.172'
check="from pathlib import Path;import json;p=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-padding-program-events-473/receipt.json');print('ready'if p.exists()and json.loads(p.read_text()).get('passed')else 'pending')"
if subprocess.check_output(['ssh',host,'python3 -c '+shlex.quote(check)],universal_newlines=True).strip()!='ready':print('473 pending; no independent480 audit launched');raise SystemExit(0)
source=(h/'control162-event-audit480-remote.py').read_text(encoding='utf-8')
q=r'''from pathlib import Path
import subprocess,json,time,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');record=b/'route-selection-102/sready480-padding-event-audit';assert not record.exists();record.mkdir();source=b/'program-event-audit480.py';assert not source.exists();source.write_bytes(SOURCE.encode());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();job=subprocess.check_output(['scontrol','show','job','95204','-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in job and 'JobName=yzl-ctl162-'in job
cmd=['srun','--jobid=95204','--exclusive','-n1','-c16','--cpu-bind=cores','/public/software/singularity-ce-4.3.4/bin/singularity','exec','--cleanenv','--bind','/public/home/yuzelu','--env','OMP_NUM_THREADS=16','--env','OPENBLAS_NUM_THREADS=1','--env','SLURM_JOB_ID=95204','/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif','bash','-c','set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 "$@"','bash',str(source)]
(record/'launch.json').write_text(json.dumps(dict(time=time.time(),source_sha256=sha(source),command=cmd,job_details=job,whole_system_qualified=False),indent=2))
with(record/'audit.stdout').open('w')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
(record/'result.json').write_text(json.dumps(dict(time=time.time(),returncode=r.returncode,stdout_sha256=sha(record/'audit.stdout'),whole_system_qualified=False),indent=2));assert r.returncode==0;print('480 actual independent event audit complete')
'''.replace('SOURCE',repr(source))
compile(q,'ready480','exec');(h/'control162-ready480-remote.py').write_bytes(q.encode());print(subprocess.check_output(['ssh',host,'python3 -c '+shlex.quote(q)],universal_newlines=True))
