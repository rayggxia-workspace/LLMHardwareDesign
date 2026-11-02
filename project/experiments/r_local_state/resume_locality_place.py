"""Legalize a completed immutable resized DB with actual inserted-buffer owners."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--capacity',type=int,required=True);a=p.parse_args()
S=a.source;D=Path.cwd()/'physical';D.mkdir(exist_ok=False);N='r166_'+str(a.capacity)
R=S/'flow/results/nangate45'/N/'base';T=D/'flow/results/nangate45'/N/'base';T.mkdir(parents=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
stage=S/'flow/logs/nangate45'/N/'base/3_4_place_resized.log'
assert 'Elapsed time:'in stage.read_text()and '3_4_place_resized'in stage.read_text()
names=['3_4_place_resized.odb','2_floorplan.sdc','1_synth.odb','1_synth.sdc','1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc']
before={str(f):sha(f)for f in [stage]+[R/n for n in names]+[S/n for n in ['input.v','input.sdc','config.mk']]}
for n in names:shutil.copyfile(R/n,T/n)
for n in ['input.v','input.sdc','pins.tcl','regions.tcl','regions.json','defer_hold.tcl','mirror_legalize.tcl']:shutil.copyfile(S/n,D/n)
shutil.copyfile(Path(__file__).parent/'buffer_locality.tcl',D/'buffer_locality.tcl')
hook=D/'mirror_legalize.tcl';hook.write_text('source {'+str(D/'buffer_locality.tcl')+'}\n'+hook.read_text())
config=(S/'config.mk').read_text().replace(str(S),str(D));(D/'config.mk').write_text(config)
commands=[];code=0;env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16')
with(D/'flow.log').open('w')as log:
 for target in ['do-3_5_place_dp','do-3_place']:
  cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(D/'config.mk'),'WORK_HOME='+str(D/'flow'),target];commands.append(cmd)
  v=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  if v.returncode:code=v.returncode;break
assert before=={f:sha(Path(f))for f in before}
(D/'receipt.json').write_text(json.dumps(dict(capacity=a.capacity,exit=code,stage='placement',source_gpl=str(S),source_unchanged=True,source_hashes=before,commands=commands,qualification_transferred=False,passed=False,acceptance_sdc_unchanged=sha(S/'input.sdc')==sha(D/'input.sdc'),change='Completed resized snapshot only; give tool-inserted data buffers real physical owners before legalizing. All original logic/SDC/final gates preserved.'),indent=2)+'\n');raise SystemExit(code)
