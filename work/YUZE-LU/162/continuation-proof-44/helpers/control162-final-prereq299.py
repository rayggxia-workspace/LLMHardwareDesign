import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
root=b/'r256-composition-274'
for p in sorted(root.glob('**/receipt.json')):
 d=json.loads(p.read_text());print(str(p.relative_to(root)),{k:v for k,v in d.items()if k in ['passed','execution_passed','typed_native_timing_passed','error','minimum_setup_ns','minimum_hold_ns']})
queue=b/'dynamic-07/node7';s=json.loads((queue/'queue-state.json').read_text());print('unfinished',s['unfinished']);print('admission',s['memory_admissions'])
for n,row in s['finished'].items():
 if '263'in n and row.get('returncode')!=0:print('failed pipeline',n,row);p=queue/(n+'.log');print(p.read_text(errors='replace').splitlines()[-12:]if p.exists()else 'no log')
'''
compile(q,'cprogress284','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
