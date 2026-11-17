import sys,re,os,json,subprocess
from pathlib import Path
c=Path(sys.argv[1]).resolve();mode=sys.argv[2]
margins={'probe':'0','h20':'.02','h50':'.05','h80':'.08'};assert mode in margins
assert json.loads((c/'accepted-leaf.json').read_text())['passed']
out=c/('parent-F-eco-'+mode+'-v3');out.mkdir()
old=Path('/public/home/yuzelu/project-circuit/main-blockv2-f300-side-01')
cfg=(c/'parent-F/config.mk').read_text()
cfg=cfg.replace(str(c/'qualification-v2/local_s_base.lef'),str(c/'parent-abstract-v3/local_s_base.lef'))
(out/'config.mk').write_text(cfg)
env=os.environ.copy()
for key in ('LIBS','LEFS'):env['F_'+key]=re.search(r'^export ADDITIONAL_'+key+r' = (.*)$',cfg,re.M)[1]
env.update(F_BASE=str(old/'flow/results/nangate45/f-native-frame/base'),F_OUT=str(out),F_MARGIN=margins[mode],F_MODE=mode,RESULTS_DIR=str(out))
with (out/'inventory.log').open('w') as f:
 subprocess.run(['openroad','-no_init','-exit',str(Path(__file__).with_name('f-original-inventory.tcl'))],cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
with (out/'implementation.log').open('w') as f:
 rc=subprocess.run(['openroad','-no_init','-exit',str(Path(__file__).with_name('f-eco-v3.tcl'))],cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
assert rc==0,rc
