import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
import collections,math
p=b/'r256-early-native-283';rows=[]
for line in (p/'typed-endpoints/endpoints.tsv').read_text().splitlines():
 n,*v=line.split('\t')
 if not all(math.isfinite(float(x))for x in v[:2])and not(v[2]=='0'and v[3]=='output'and v[4]=='0'):rows.append((n,v))
print('unconstrained-retained',len(rows),'port-direction-counts',dict(collections.Counter((v[2],v[3])for n,v in rows)),'examples',rows[:4])
for name in ['r256-fixed-pg-291/checks/timing','r256-fixed-pg-291/delivery','r256-composition-274/selected','r256-composition-274/native-sta']:
 p=b/name;r=p/'receipt.json';d=json.loads(r.read_text())if r.exists()else{};print(name,{k:v for k,v in d.items()if k in ['passed','timing_passed','minimum_setup_ns','minimum_hold_ns','execution_passed','typed_native_timing_passed']})
'''
compile(q,'cprogress284','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
