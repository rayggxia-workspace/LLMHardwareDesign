import sys,re,os,json,subprocess
from pathlib import Path
c=Path(sys.argv[1]).resolve();mode=sys.argv[2]
margins={'h20':'.02','h50':'.05','h80':'.08'};assert mode in margins
assert json.loads((c/'accepted-leaf.json').read_text())['passed']
out=c/('parent-F-eco-'+mode);out.mkdir()
old=Path('/public/home/yuzelu/project-circuit/main-blockv2-f300-side-01')
cfg=(c/'parent-F/config.mk').read_text()
cfg=cfg.replace(str(c/'qualification-v2/local_s_base.lef'),str(c/'abstract-detailed/local_s_base.lef'))
(out/'config.mk').write_text(cfg)
env=os.environ.copy()
for key in ('LIBS','LEFS'):env['F_'+key]=re.search(r'^export ADDITIONAL_'+key+r' = (.*)$',cfg,re.M)[1]
env.update(F_BASE=str(old/'flow/results/nangate45/f-native-frame/base'),F_OUT=str(out),F_MARGIN=margins[mode],RESULTS_DIR=str(out))
with (out/'implementation.log').open('w') as f:
 rc=subprocess.run(['openroad','-no_init','-exit',str(Path(__file__).with_name('f-eco.tcl'))],cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
assert rc==0,rc
