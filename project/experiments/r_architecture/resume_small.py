"""Fresh post-CTS physical repair; preserve the completed failed trial."""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess

p=argparse.ArgumentParser()
p.add_argument('--source',required=True)
p.add_argument('--setup-margin',type=float,default=.15)
p.add_argument('--hold-margin',type=float,default=.10)
p.add_argument('--strong-clock',action='store_true')
a=p.parse_args()
assert re.fullmatch(r'attempt[0-9]+(?:/B[0-9]+)?',a.source)
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
src=base/a.source/'physical';dst=Path.cwd()/'physical'
rec=json.loads((src/'receipt.json').read_text());assert rec['exit']==0
c=rec['candidate'];assert c in ['B256','B1024']
assert 0<a.setup_margin<=.3 and 0<a.hold_margin<=.2
assert not dst.exists();dst.mkdir()
def sha(f):
 h=hashlib.sha256()
 with f.open('rb')as s:
  for b in iter(lambda:s.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
names=['config.mk','input.v','input.sdc','flow/results/nangate45/rarch157_'+c+'/base/4_cts.odb',
       'flow/results/nangate45/rarch157_'+c+'/base/4_cts.sdc']
if a.strong_clock:
 names+=['flow/results/nangate45/rarch157_'+c+'/base/3_place.odb',
         'flow/results/nangate45/rarch157_'+c+'/base/3_place.sdc']
before={n:sha(src/n)for n in names}
subprocess.run(['cp','-a','--reflink=auto',str(src/'flow'),str(dst/'flow')],check=True)
config=(src/'config.mk').read_text()
config=re.sub(r'^export HOLD_SLACK_MARGIN = .*$',f'export HOLD_SLACK_MARGIN = {a.hold_margin}',config,flags=re.M)
config+=f'\nexport SETUP_SLACK_MARGIN = {a.setup_margin}\n'
if a.strong_clock:
 # CTS_ARGS replaces the inferred argument list in this ORFS version.
 config+='export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -apply_ndr none -buf_list {CLKBUF_X3 BUF_X8 BUF_X16} -root_buf BUF_X16\n'
(dst/'config.mk').write_text(config)
for name in ['input.sdc','IMPLEMENTATION.json']:
 subprocess.run(['cp',str(src/name),str(dst/name)],check=True)
env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16')
commands=[];exitcode=0;screen=None
targets=['do-5_1_grt','do-5_2_route','do-5_3_fillcell','do-5_route',
         'do-5_route.sdc','do-6_1_fill','do-6_1_fill.sdc','do-6_report']
if a.strong_clock:targets=['do-4_1_cts','do-4_cts']+targets
with(dst/'flow.log').open('w')as log:
 for target in targets:
  cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(dst/'config.mk'),
       'WORK_HOME='+str(dst/'flow'),target]
  commands.append(cmd);r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  if r.returncode:exitcode=r.returncode;break
  if a.strong_clock and target=='do-4_1_cts':
   f=dst/'flow/logs/nangate45'/('rarch157_'+c)/'base/4_1_cts.json'
   v=json.loads(f.read_text());screen=dict(metrics=v,passed=
    v['cts__timing__setup__ws']>=0 and v['cts__timing__hold__ws']>=0 and
    all(v[k]==0 for k in ['cts__timing__drv__max_cap','cts__timing__drv__max_slew',
     'cts__timing__drv__setup_violation_count','cts__timing__drv__hold_violation_count']))
   if not screen['passed']:exitcode=3;break
assert before=={n:sha(src/n)for n in names}
rec.update(exit=exitcode,commands=commands,source=str(src),source_unchanged=True,
           source_sha256=before,setup_repair_margin_ns=a.setup_margin,
           hold_repair_margin_ns=a.hold_margin,qualification_transferred=False)
rec.update(strong_clock=a.strong_clock,cts_screen=screen)
(dst/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
raise SystemExit(exitcode)
