"""Preserve accepted short-pin input protection and add measured setup margin before rerouting."""
from pathlib import Path
import argparse,subprocess,json,hashlib,os,shutil,re
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--capacity',type=int,required=True);p.add_argument('--path-evidence',type=Path);p.add_argument('--short-clock',action='store_true');a=p.parse_args()
S=a.source;D=Path.cwd()/'physical';D.mkdir(exist_ok=False);N='r166_'+str(a.capacity);R=S/'flow/results/nangate45'/N/'base';T=D/'flow/results/nangate45'/N/'base';T.mkdir(parents=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
names=['4_cts.odb','4_cts.sdc','1_synth.odb','1_synth.sdc','1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc'];protected=[R/n for n in names]+[S/n for n in ['input.v','input.sdc','config.mk']];before={str(f):sha(f)for f in protected}
for n in names:shutil.copyfile(R/n,T/n)
for n in ['input.v','input.sdc','pins.tcl','regions.tcl','regions.json','defer_hold.tcl','mirror_legalize.tcl','hold_endpoints.tcl','input_hold.tcl']:shutil.copyfile(S/n,D/n)
shutil.copyfile(Path(__file__).parent/'io_protect.tcl',D/'io_protect.tcl')
config=(S/'config.mk').read_text().replace(str(S),str(D))
# 20ps was a repair target, never an acceptance waiver. Stop padding paths
# already above the unchanged exact0ns final hold gate; original SDC is copied.
config=re.sub(r'^export HOLD_SLACK_MARGIN = .*$', 'export HOLD_SLACK_MARGIN = 0',config,flags=re.M)
config=re.sub(r'^export SETUP_SLACK_MARGIN = .*$', 'export SETUP_SLACK_MARGIN = 0.060',config,flags=re.M)
config+='\nexport PRE_GLOBAL_ROUTE_TCL = '+str(D/'io_protect.tcl')+'\n'
if a.path_evidence:
 evidence=json.loads((a.path_evidence/'receipt.json').read_text());assert evidence['passed']
 for f,h in evidence['inputs'].items():assert sha(Path(f))==h
 rows=[r.split('\t')for r in(a.path_evidence/'failing-paths.tsv').read_text().splitlines()]
 assert rows and all(r[0]=='min'and'/'not in r[1]and float(r[3])<0 for r in rows),'Only measured external hold paths supported'
 worst={}
 for r in rows:worst[r[1]]=min(worst.get(r[1],0),float(r[3]))
 assert len(worst)<=4 and all(s>-.1 for s in worst.values())
 (D/'EXTRACTED_PATH_BINDING.json').write_text(json.dumps({'diagnosis':str(a.path_evidence),'inputs':evidence['inputs'],'rows':rows},indent=2)+'\n')
 (D/'extra_input.tcl').write_text('set r166_extra_ports [dict create '+' '.join('{'+n+'} '+str(s)for n,s in worst.items())+']\n'+(Path(__file__).parent/'extra_input.tcl').read_text())
 with(D/'io_protect.tcl').open('a')as f:f.write('\nsource '+str(D/'extra_input.tcl')+'\n')
if a.short_clock:
 shutil.copyfile(Path(__file__).parent/'short_clock.tcl',D/'short_clock.tcl')
 with(D/'io_protect.tcl').open('a')as f:f.write('\nsource '+str(D/'short_clock.tcl')+'\n')
(D/'config.mk').write_text(config)
env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16');commands=[];code=0
with(D/'flow.log').open('w')as log:
 for target in ['do-5_1_grt','do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-6_1_fill','do-6_1_fill.sdc','do-6_report']:
  cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(D/'config.mk'),'WORK_HOME='+str(D/'flow'),target];commands.append(cmd);v=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  if v.returncode:code=v.returncode;break
assert before=={f:sha(Path(f))for f in before}
(D/'receipt.json').write_text(json.dumps({'capacity':a.capacity,'exit':code,'source_cts':str(S),'source_unchanged':True,'source_hashes':before,'commands':commands,'qualification_transferred':False,'passed':False,'acceptance_sdc_unchanged':sha(S/'input.sdc')==sha(D/'input.sdc'),'change':'Reuse original qualified small-R input BUF_X16 protection on every actual loaded data input; fixed short-pin drivers have explicit physical ownership. Global setup optimization margin60ps targets measured19ps GRT-to-RCX loss; original300MHz/IO and all final exact nonnegative/zero-violation gates unchanged'},indent=2)+'\n');raise SystemExit(code)
