from pathlib import Path
import os,sys,re,subprocess,hashlib,json
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
src=root/'cu/runs/C-v13-exactio-macropdn-distributed-parallel'
assert json.loads((src/'geometry-prects-contract.json').read_text())['signal_die_macro_exact']
seed=src/'flow/results/nangate45/c-overlay-current/base'
size,weight=sys.argv[1:]
out=root/f'cluster/size{size}-weight{weight}'
out.mkdir(parents=True,exist_ok=False)
config=(src/'config.mk').read_text()
libs=re.findall(r'^export ADDITIONAL_LIBS\s*=\s*(.+)$',config,re.M)[-1]
env=os.environ|{'CC_LIBS':libs,'CC_SEED':str(seed),'CC_SIZE':size,'CC_WEIGHT':weight}
inputs=[seed/'3_place.odb',seed/'3_place.sdc',src/'config.mk',root/'c-cluster.tcl']
(out/'inputs.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},indent=2)+'\n')
with (out/'run.log').open('w') as f:
    rc=subprocess.run(['/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit',str(root/'c-cluster.tcl')],cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
(out/'exit-code.txt').write_text(str(rc)+'\n')
sys.exit(rc)
