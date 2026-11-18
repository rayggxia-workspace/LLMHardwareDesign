from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');old=r/'audit/C-antenna-main-v2';p=r/'audit/C-antenna-v27-r2';p.mkdir(exist_ok=False)
for n in ('hook.tcl','build.py','structural-state.tcl','dry-edit.tcl','readback.tcl','dry-edit.sbatch','freeze-package.py'):
 s=(old/n).read_text().replace('C-antenna-main-v2','C-antenna-v27-r2').replace('C-v20-native-clock4-119976','C-v27-joint-e20-h30-120037').replace('C-v20-native-clock4','C-v27-joint-e20-h30').replace('549','17').replace('audit/C-main-clock4-physical-v1/focused','audit/C-v27-physical/focused')
 if n=='build.py':
  import hashlib
  sha=hashlib.sha256((r/'cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.gds').read_bytes()).hexdigest();s=s.replace('7a469744bc6a08962009c1e37039dd89385a8fc188412cfa4e1b2b542342dbe2',sha)
 (p/n).write_text(s)
