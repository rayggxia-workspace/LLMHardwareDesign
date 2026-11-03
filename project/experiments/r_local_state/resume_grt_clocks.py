"""Resume exact zero-violation GRT after a diagnosed pre-detail clock failure."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
from fixed_clock_routes import audit
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--probe',type=Path,required=True);a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
S=a.source;P=Path(__file__).resolve().parent;R=S/'flow/results/nangate45/r166_1024/base'
old=json.loads((S/'receipt.json').read_text());assert old['capacity']==1024 and old['exit']==2 and old['source_unchanged']
assert 'fixed_clock_before-detail.tcl'in(S/'flow.log').read_text()and not(R/'6_final.odb').exists()
probe=json.loads((a.probe/'receipt.json').read_text());assert probe['passed']and probe['physical']==str(S)and probe['qualification']is False and probe['precheck']['producer_sha256']==sha(P/'fixed_clock_routes.py')
for name,digest in probe['inputs'].items():assert sha(Path(name))==digest
metrics=S/'flow/logs/nangate45/r166_1024/base/5_1_grt.json';m=json.loads(metrics.read_text())
for key in ['setup_violation_count','hold_violation_count','max_cap','max_slew']:assert m['globalroute__timing__drv__'+key]==0
assert m['globalroute__timing__setup__ws']>=0 and m['globalroute__timing__hold__ws']>=0
names=['CLOCK_ROUTE_BINDING.json','CLOCK_BASELINE.json.gz','CLOCK_FIXED.def','CLOCK_NATIVE_NAMES.tsv','clock_source_names.tcl','CLOCK_LOCKED_CELLS.tsv','input.v','input.sdc','regions.json']
files=[f for f in R.iterdir()if f.is_file()and(f.name.startswith(('1_','4_','5_1_grt.'))or f.name in ['route.guide','updated_clks.sdc'])]
assert {'5_1_grt.odb','5_1_grt.sdc','route.guide'}<={f.name for f in files}
protected=[S/n for n in names]+files+[S/'receipt.json',S/'config.mk',S/'flow.log',S/'GRT_CLOSURE.tsv',metrics,a.probe/'receipt.json']
before={str(f):sha(f)for f in protected}
D=Path.cwd()/'physical';D.mkdir(exist_ok=False);T=D/'flow/results/nangate45/r166_1024/base';T.mkdir(parents=True)
for f in files:shutil.copyfile(f,T/f.name)
for name in names:shutil.copyfile(S/name,D/name)
# Preserve generated Tcl inputs without executing their GRT hooks again.
for f in S.glob('*.tcl'):
 if not(D/f.name).exists():shutil.copyfile(f,D/f.name)
binding=json.loads((D/'CLOCK_ROUTE_BINDING.json').read_text());binding.update(restoration_protocol='exact-source-clock-restore-v1',resumed_from_clock_binding_sha256=sha(S/'CLOCK_ROUTE_BINDING.json'),scope='Exact source zero-violation GRT checkpoint; restore original source clocks after strict precheck, then all three complete geometry audits and every original final physical/function gate. No qualification transfer.')
(D/'CLOCK_ROUTE_BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
for phase in ['before-detail','after-detail']:
 text='set here {'+str(D)+'}\n'
 if phase=='before-detail':
  text+='write_def {'+str(D/'CLOCK_pre-restore.def')+'}\nputs [exec python3 {'+str(P/'fixed_clock_routes.py')+'} precheck --physical {'+str(D)+'} --def {'+str(D/'CLOCK_pre-restore.def')+'}]\nread_def -floorplan_initialize {'+str(D/'CLOCK_FIXED.def')+'}\n'
 text+='write_def {'+str(D/('CLOCK_'+phase+'.def'))+'}\nputs [exec python3 {'+str(P/'fixed_clock_routes.py')+'} audit --physical {'+str(D)+'} --def {'+str(D/('CLOCK_'+phase+'.def'))+'} --phase '+phase+']\n'
 (D/('fixed_clock_'+phase+'.tcl')).write_text(text)
config=(S/'config.mk').read_text().replace(str(S),str(D));(D/'config.mk').write_text(config)
resume=dict(source=str(S),checkpoint=str(R/'5_1_grt.odb'),checkpoint_sha256=sha(R/'5_1_grt.odb'),metrics=str(metrics),metrics_sha256=sha(metrics),probe=str(a.probe),probe_receipt_sha256=sha(a.probe/'receipt.json'),inputs=before,qualification_transferred=False,scope='Reuse only exact successful GRT stage of an actually failed pre-detail run. All final files must be freshly produced and all original physical/function/clock acceptance gates rerun.')
(D/'GRT_RESUME.json').write_text(json.dumps(resume,indent=2)+'\n')
env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16');commands=[];code=0
with(D/'flow.log').open('w')as log:
 for target in ['do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-6_1_fill','do-6_1_fill.sdc','do-6_report']:
  cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(D/'config.mk'),'WORK_HOME='+str(D/'flow'),target];commands.append(cmd);r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  if r.returncode:code=r.returncode;break
assert all(sha(Path(f))==v for f,v in before.items())
if code==0:audit(D,T/'6_final.def','final')
(D/'receipt.json').write_text(json.dumps(dict(capacity=1024,exit=code,source_grt=str(S),source_unchanged=True,source_hashes=before,commands=commands,qualification_transferred=False,passed=False,acceptance_sdc_unchanged=sha(S/'input.sdc')==sha(D/'input.sdc'),change='Exact successful GRT-stage reuse; original source clock restoration and fresh complete DRT/RCX/final gates required.'),indent=2)+'\n');raise SystemExit(code)
