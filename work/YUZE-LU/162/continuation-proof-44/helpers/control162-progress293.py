from pathlib import Path
import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
for name in ['r256-fixed-pg-272/wrapper','r256-fixed-pg-272/checks/physical','r256-fixed-pg-291/checks/timing','r256-fixed-pg-291/delivery','r256-fixed-pg-271/2371/wrapper','r256-composition-259/topology','r256-composition-273/function','r256-early-electrical-266/initial','r256-early-electrical-277/optimized','r256-early-native-283','r256-composition-274/selected','r256-composition-274/native-sta']:
 p=b/name; r=p/'receipt.json'; print(name,'RECEIPT',{k:v for k,v in json.loads(r.read_text()).items()if k in ['passed','stage','native_drc_zero','timing_passed','minimum_setup_ns','minimum_hold_ns','error','whole_system_qualified']} if r.exists()else 'unfinished')
 if not r.exists():
  logs=sorted(p.rglob('*.log'),key=lambda x:x.stat().st_mtime);print('latest logs',[(str(x.relative_to(p)),[line[:220]for line in x.read_text(errors='replace').splitlines()[-2:]])for x in logs[-2:]])
'''
compile(q,'latest262','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
