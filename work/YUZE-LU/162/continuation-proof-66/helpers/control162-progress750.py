import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-pair-window-regression-736');rows=[]
for p in b.rglob('router.log'):
 if not any(x.startswith(('window','trace','weight'))for x in p.relative_to(b).parts):continue
 with p.open('rb')as f:f.seek(0,2);f.seek(max(0,f.tell()-600));tail=f.read().decode(errors='replace')
 rows.append(dict(case=str(p.parent.relative_to(b)),output=(p.parent/'router-output.txt').exists(),tail=tail[-300:]))
print(json.dumps(dict(case_logs=len(rows),completed=sum(x['output']for x in rows),window=[x for x in rows if any(v.startswith('window')for v in x['case'].split('/'))],incomplete=[x for x in rows if not x['output']][:3])))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
