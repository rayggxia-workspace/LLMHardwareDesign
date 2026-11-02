"""Use measured endpoint hold repair instead of a nonconverging broad hold sweep."""
from pathlib import Path
import argparse,subprocess,json,hashlib,os,shutil,re
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--capacity',type=int,required=True);p.add_argument('--diamond',action='store_true');p.add_argument('--strong-clock',action='store_true');p.add_argument('--cts-only',action='store_true');p.add_argument('--buffer-locality',action='store_true');a=p.parse_args()
S=a.source;D=Path.cwd()/'physical';D.mkdir(exist_ok=False);N='r166_'+str(a.capacity);R=S/'flow/results/nangate45'/N/'base';T=D/'flow/results/nangate45'/N/'base';T.mkdir(parents=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
names=['3_place.odb','3_place.sdc','1_synth.odb','1_synth.sdc','1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc'];protected=[R/n for n in names]+[S/n for n in ['input.v','input.sdc','config.mk']];before={str(f):sha(f)for f in protected}
for n in names:shutil.copyfile(R/n,T/n)
for n in ['input.v','input.sdc','pins.tcl','regions.tcl','regions.json','defer_hold.tcl','mirror_legalize.tcl']:shutil.copyfile(S/n,D/n)
shutil.copyfile(Path(__file__).parent/'hold_endpoints.tcl',D/'hold_endpoints.tcl')
shutil.copyfile(Path(__file__).parent/'input_hold.tcl',D/'input_hold.tcl')
if a.buffer_locality:
 shutil.copyfile(Path(__file__).parent/'buffer_locality.tcl',D/'buffer_locality.tcl')
 with(D/'defer_hold.tcl').open('a')as f:f.write('\nsource {'+str(D/'buffer_locality.tcl')+'}\n')
if a.diamond:
 with(D/'defer_hold.tcl').open('a')as f:f.write('rename detailed_placement detailed_placement_negotiation\nproc detailed_placement {args} {detailed_placement_negotiation -use_diamond_legalizer {*}$args}\nputs R166_DIAMOND_LEGALIZER_ACTUAL_REGION_CHECKS_UNCHANGED\n')
config=(S/'config.mk').read_text().replace(str(S),str(D))
config+='\nexport PRE_CTS_TCL = '+str(D/'defer_hold.tcl')+'\nexport POST_CTS_TCL = '+str(D/'input_hold.tcl')+'\n'
if a.strong_clock:
 config=re.sub(r'^export CTS_ARGS = .*$', 'export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -apply_ndr none -buf_list {BUF_X8} -root_buf BUF_X16 -sink_clustering_size 32 -balance_levels',config,flags=re.M)
 config=re.sub(r'^export HOLD_SLACK_MARGIN = .*$', 'export HOLD_SLACK_MARGIN = 0',config,flags=re.M)
(D/'config.mk').write_text(config)
env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16');commands=[];code=0
with(D/'flow.log').open('w')as log:
 for target in ['do-4_1_cts','do-4_cts']+([]if a.cts_only else['do-5_1_grt','do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-6_1_fill','do-6_1_fill.sdc','do-6_report']):
  cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(D/'config.mk'),'WORK_HOME='+str(D/'flow'),target];commands.append(cmd);v=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  if v.returncode:code=v.returncode;break
assert before=={f:sha(Path(f))for f in before}
(D/'receipt.json').write_text(json.dumps({'capacity':a.capacity,'exit':code,'stage':'cts'if a.cts_only else'finish','source_placed':str(S),'source_unchanged':True,'source_hashes':before,'commands':commands,'qualification_transferred':False,'passed':False,'acceptance_sdc_unchanged':sha(S/'input.sdc')==sha(D/'input.sdc'),'change':'Default real clock tree; measured failing input startpoints receive shared delay chains before any residual endpoint hold ECO; original300MHz/IO and all final zero-violation gates unchanged'},indent=2)+'\n');raise SystemExit(code)
