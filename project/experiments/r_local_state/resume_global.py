"""Reroute real CTS without a nonconverging positive-only optimizer margin."""
from pathlib import Path
import argparse,subprocess,json,hashlib,os,shutil,re
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--capacity',type=int,required=True);a=p.parse_args()
S=a.source;D=Path.cwd()/'physical';D.mkdir(exist_ok=False);N='r166_'+str(a.capacity);R=S/'flow/results/nangate45'/N/'base';T=D/'flow/results/nangate45'/N/'base';T.mkdir(parents=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
names=['4_cts.odb','4_cts.sdc','1_synth.odb','1_synth.sdc','1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc'];protected=[R/n for n in names]+[S/n for n in ['input.v','input.sdc','config.mk']];before={str(f):sha(f)for f in protected}
for n in names:shutil.copyfile(R/n,T/n)
for n in ['input.v','input.sdc','pins.tcl','regions.tcl','regions.json','defer_hold.tcl','mirror_legalize.tcl','hold_endpoints.tcl','input_hold.tcl']:shutil.copyfile(S/n,D/n)
config=(S/'config.mk').read_text().replace(str(S),str(D))
# 20ps was a repair target, never an acceptance waiver. Stop padding paths
# already above the unchanged exact0ns final hold gate; original SDC is copied.
config=re.sub(r'^export HOLD_SLACK_MARGIN = .*$', 'export HOLD_SLACK_MARGIN = 0',config,flags=re.M)
(D/'config.mk').write_text(config)
env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16');commands=[];code=0
with(D/'flow.log').open('w')as log:
 for target in ['do-5_1_grt','do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-6_1_fill','do-6_1_fill.sdc','do-6_report']:
  cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(D/'config.mk'),'WORK_HOME='+str(D/'flow'),target];commands.append(cmd);v=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  if v.returncode:code=v.returncode;break
assert before=={f:sha(Path(f))for f in before}
(D/'receipt.json').write_text(json.dumps({'capacity':a.capacity,'exit':code,'source_cts':str(S),'source_unchanged':True,'source_hashes':before,'commands':commands,'qualification_transferred':False,'passed':False,'acceptance_sdc_unchanged':sha(S/'input.sdc')==sha(D/'input.sdc'),'change':'Source already contains measured shared-input and residual endpoint delay ECO. Global optimizer hold target0ns instead of20ps to avoid repeated padding at positive17ps plateau; original300MHz/IO and every exact final nonnegative/zero-violation gate unchanged'},indent=2)+'\n');raise SystemExit(code)
