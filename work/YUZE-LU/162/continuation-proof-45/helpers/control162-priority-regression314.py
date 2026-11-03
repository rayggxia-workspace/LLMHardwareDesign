import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
import sys,hashlib,time
source=b/'source-313/project/experiments/control_v1';sys.path.insert(0,str(source));from test_priority_outputs import inspect
out=b/'r256-priority-regression-314';assert not out.exists();out.mkdir();graphs=[(b/'s-ready-composition-01/1391/topology/boundary-graph.json',583),(b/'r256-composition-274/topology/boundary-graph.json',1229)];results=[inspect(p,n)for p,n in graphs];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();inputs={str(p):sha(p)for p in [source/'system_upper.py',source/'test_priority_outputs.py']+[p for p,n in graphs]};r=dict(passed=all(row['passed']and row['legacy_subsequence_exact']for row in results),results=results,inputs=inputs,time=time.time(),whole_system_qualified=False,scope='Actual legacy583 membership/order byte-equivalent selection and genuine R2561229 priority roots, including all646 R output nets. Every actual sink must be one existing Link8 receiver. Missing R output negative rejected. Search-only optional priority budgets; no physical/RC qualification. Lightweight graph-only test on login, no EDA/new allocation.');(out/'receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(dict(passed=r['passed'],results=results)))
'''
compile(q,'cprogress284','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
