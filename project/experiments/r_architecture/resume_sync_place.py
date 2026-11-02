"""Bounded sync-R1024 retry: avoid excessive pre-clock hold padding."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
p=argparse.ArgumentParser();p.add_argument('--defer-hold',action='store_true');p.add_argument('--buffer-inputs',action='store_true');a=p.parse_args()
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
src=base/'attempt082/physical';dst=Path.cwd()/'physical';candidate='B1024S'
root=src/'flow/results/nangate45/rarch157_B1024S/base'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
log=(src/'flow.log').read_text();assert '100001'in log and '0.026'in log
names=['3_3_place_gp.odb','2_floorplan.sdc','1_synth.odb','1_synth.sdc','1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc']
protected=[root/n for n in names]+[src/n for n in ['config.mk','input.v','input.sdc','IMPLEMENTATION.json']]
before={str(p):sha(p)for p in protected}
dst.mkdir(exist_ok=False);fresh=dst/'flow/results/nangate45/rarch157_B1024S/base';fresh.mkdir(parents=True)
for name in names:shutil.copyfile(root/name,fresh/name)
for name in ['input.v','input.sdc','IMPLEMENTATION.json']:shutil.copyfile(src/name,dst/name)
config=(src/'config.mk').read_text()
pre_hold=0 if a.defer_hold else .02
config=re.sub(r'^export HOLD_SLACK_MARGIN = .*$', 'export HOLD_SLACK_MARGIN = '+str(pre_hold),config,flags=re.M)
config+='\nexport CTS_ARGS = -sink_clustering_enable -repair_clock_nets -apply_ndr none -buf_list {CLKBUF_X3 BUF_X8 BUF_X16} -root_buf BUF_X16\n'
if a.buffer_inputs:
 # Apply the measured R256 input-access recipe to all loaded nonclock inputs.
 # No geometry/clock/SDC exception or antenna-check suppression is introduced.
 shutil.copyfile(Path(__file__).parent/'port_buffers.tcl',dst/'port_buffers.tcl')
 (dst/'required_ports.tcl').write_text('set r157_required_ports {}\n')
 config+='export PRE_GLOBAL_ROUTE_TCL = '+str(dst/'port_buffers.tcl')+'\n'
(dst/'config.mk').write_text(config)
env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16')
commands=[];exitcode=0;screen=None
targets=['do-3_4_place_resized','do-3_5_place_dp','do-3_place','do-4_1_cts','do-4_cts','do-5_1_grt','do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-6_1_fill','do-6_1_fill.sdc','do-6_report']
with(dst/'flow.log').open('w')as f:
 for target in targets:
  if target=='do-4_1_cts':
   config+='\nexport HOLD_SLACK_MARGIN = .06\n';(dst/'config.mk').write_text(config)
  cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(dst/'config.mk'),'WORK_HOME='+str(dst/'flow'),target]
  commands.append(cmd);r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
  if r.returncode:exitcode=r.returncode;break
  if target=='do-4_1_cts':
   v=json.loads((dst/'flow/logs/nangate45/rarch157_B1024S/base/4_1_cts.json').read_text())
   screen=dict(metrics=v,passed=v['cts__timing__setup__ws']>=0 and v['cts__timing__hold__ws']>=0 and all(v[k]==0 for k in ['cts__timing__drv__max_cap','cts__timing__drv__max_slew','cts__timing__drv__setup_violation_count','cts__timing__drv__hold_violation_count']))
   if not screen['passed']:exitcode=3;break
assert before=={str(p):sha(p)for p in protected}
rec=dict(candidate=candidate,capacity=1024,exit=exitcode,commands=commands,source=str(src),source_unchanged=True,source_sha256=before,reason='measured excessive pre-clock hold padding; stage hold repair with actual strong CTS',pre_clock_hold_margin_ns=pre_hold,post_clock_hold_margin_ns=.06,buffer_inputs=a.buffer_inputs,cts_screen=screen,qualification_transferred=False)
(dst/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');raise SystemExit(exitcode)
