from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');old=r/'audit/C-antenna-eco-v1';new=r/'audit/C-antenna-main-v2';new.mkdir(exist_ok=False)
for name in ('hook.tcl','build.py','structural-state.tcl','dry-edit.tcl','readback.tcl','dry-edit.sbatch','freeze-package.py'):
 s=(old/name).read_text(encoding='utf-8-sig').replace('C-antenna-eco-v1','C-antenna-main-v2').replace('C-v22-access-metal1-119959','C-v20-native-clock4-119976').replace('C-v22-access-metal1','C-v20-native-clock4').replace('547','549').replace('2cdeffb831ef0948ac87fc521b9322e300dcd70e10b9eb30492f89fc03168a9d','7a469744bc6a08962009c1e37039dd89385a8fc188412cfa4e1b2b542342dbe2').replace('c-physical/focused-C-v20-native-clock4/antenna-binding.json','audit/C-main-clock4-physical-v1/focused/antenna-binding.json')
 (new/name).write_text(s)
