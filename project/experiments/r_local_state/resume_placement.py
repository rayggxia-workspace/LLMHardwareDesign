"""Resume an exact GPL snapshot; do hold repair only after a real clock tree."""
from pathlib import Path
import argparse,subprocess,hashlib,json,os,shutil
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--capacity',type=int,required=True);p.add_argument('--resized-from',type=Path);a=p.parse_args()
S=a.source;D=Path.cwd()/'physical';D.mkdir(exist_ok=False);N='r166_'+str(a.capacity);R=S/'flow/results/nangate45'/N/'base';T=D/'flow/results/nangate45'/N/'base';T.mkdir(parents=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
log=(S/'flow.log').read_text();assert all(('Region name: r166_b'+str(b)+'_g'+str(g)+'_cells.')in log for b in range(2)for g in range(a.capacity//128))
names=['3_3_place_gp.odb','2_floorplan.sdc','1_synth.odb','1_synth.sdc','1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc']
protected=[R/n for n in names]+[S/n for n in ['input.v','input.sdc','config.mk']];before={str(f):sha(f)for f in protected}
for n in names:shutil.copyfile(R/n,T/n)
for n in ['input.v','input.sdc','pins.tcl','regions.tcl','regions.json']:shutil.copyfile(S/n,D/n)
(D/'defer_hold.tcl').write_text('rename repair_timing_helper repair_timing_after_cts\nproc repair_timing_helper {args} {repair_timing_after_cts -setup {*}$args}\nputs "R166_PRE_CTS_SETUP_ONLY_FINAL_HOLD_UNCHANGED"\n')
(D/'mirror_legalize.tcl').write_text('rename optimize_mirroring optimize_mirroring_native\nproc optimize_mirroring {args} {optimize_mirroring_native {*}$args; detailed_placement_helper; puts \"R166_RELEGALIZED_AFTER_MIRROR\"}\n')
config=(S/'config.mk').read_text().replace(str(S),str(D))+'\nexport PRE_RESIZE_TCL = '+str(D/'defer_hold.tcl')+'\nexport PRE_DETAIL_PLACE_TCL = '+str(D/'mirror_legalize.tcl')+'\n';(D/'config.mk').write_text(config)
env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16');commands=[];code=0
if a.resized_from:
 X=a.resized_from;assert json.loads((X/'receipt.json').read_text())['source_gpl']==str(S)
 assert sha(X/'input.sdc')==sha(S/'input.sdc') and sha(X/'input.v')==sha(S/'input.v')
 f=X/'flow/results/nangate45'/N/'base/3_4_place_resized.odb';before[str(f)]=sha(f);shutil.copyfile(f,T/f.name)
with(D/'flow.log').open('w')as log:
 for target in ['do-3_4_place_resized','do-3_5_place_dp','do-3_place','do-4_1_cts','do-4_cts','do-5_1_grt','do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-6_1_fill','do-6_1_fill.sdc','do-6_report']:
  if target=='do-3_4_place_resized' and a.resized_from:continue
  cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(D/'config.mk'),'WORK_HOME='+str(D/'flow'),target];commands.append(cmd)
  result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  if result.returncode:code=result.returncode;break
assert before=={f:sha(Path(f))for f in before}
(D/'receipt.json').write_text(json.dumps({'capacity':a.capacity,'exit':code,'source_gpl':str(S),'source_unchanged':True,'source_hashes':before,'commands':commands,'qualification_transferred':False,'passed':False,'acceptance_sdc_unchanged':sha(S/'input.sdc')==sha(D/'input.sdc'),'change':'Pre-CTS setup-only repair; all original SDC, 0.02ns post-CTS hold optimization, and final electrical/STA gates unchanged'},indent=2)+'\n');raise SystemExit(code)
