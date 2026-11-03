"""Discover the exact new source only after unchanged original acceptance code checks."""
from pathlib import Path
import subprocess,shlex,json
q=r'''from pathlib import Path
import json,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');paths=['system_geometry.py','system_accept.py','system_sta.py','system_pg_audit.py','system_native_audit.py','upper_rc_network.py','native_stitch.py','boundary_links.py'];rows=[]
for name in paths:
 p=b/'source-172/project/experiments/control_v1'/name;old=b/'source-140/project/experiments/control_v1'/name;digest=hashlib.sha256(p.read_bytes()).hexdigest();assert digest==hashlib.sha256(old.read_bytes()).hexdigest();rows.append(dict(name=name,sha256=digest))
record=b/'route-selection-102/s-ready-fastroute24phase-source172.json';d=json.loads(record.read_text());assert d['source']=='source-172'and d['instance_count']==235 and d['selected_adapter_candidate']==1391 and len(d['tasks'])==7
for r in d['tasks']:assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256']
print(json.dumps(dict(passed=True,unchanged_acceptors=rows,record=str(record),record_sha256=hashlib.sha256(record.read_bytes()).hexdigest(),whole_system_qualified=False)))
'''
result=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45));assert result['passed']
home=Path(r'D:\Data\电路实验');out=home/'control162-collector177-source-proof.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
for name in ['control162-system-ready140.py','control162-final-receipts-retry140.py','control162-next-gate143.py']:
 p=home/name;s=p.read_text(encoding='utf-8');old="'s-ready-local-density-openroad-source157.json'";new="'s-ready-fastroute24phase-source172.json'";assert s.count(old)==1 and new not in s;s=s.replace(old,old+','+new)
 if name!='control162-next-gate143.py':
  old="'source-156','source-157']";assert s.count(old)==1;s=s.replace(old,"'source-156','source-157','source-172']")
 compile(s,name,'exec');p.write_text(s,encoding='utf-8');print(name,'exact source172 record; original eight final acceptor SHA unchanged')
