"""Recover the timed-out A1 final report in a fresh directory, never in place."""
from pathlib import Path
import subprocess,json,hashlib,os

src=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt044/physical')
dst=Path.cwd()/'physical'
assert not dst.exists()
dst.mkdir()
before={n:hashlib.sha256((src/n).read_bytes()).hexdigest() for n in
        ['config.mk','input.sdc','flow/results/nangate45/rarch157_A1/base/6_1_fill.odb',
         'flow/results/nangate45/rarch157_A1/base/6_1_fill.sdc']}
subprocess.run(['cp','-a','--reflink=auto',str(src/'flow'),str(dst/'flow')],check=True)
# Rebind only this fresh output tree; immutable input V/pins remain read-only.
config=(src/'config.mk').read_text()
(dst/'config.mk').write_text(config)
env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16')
cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(dst/'config.mk'),
     'WORK_HOME='+str(dst/'flow'),'do-6_report']
with (dst/'fresh-final-report.log').open('w') as f:
    r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
after={n:hashlib.sha256((src/n).read_bytes()).hexdigest() for n in before}
assert before==after
(dst/'RECOVERY.json').write_text(json.dumps(dict(source=str(src),source_unchanged=True,
    source_sha256=before,command=cmd,exit=r.returncode,qualification_transferred=False),indent=2)+'\n')
raise SystemExit(r.returncode)
