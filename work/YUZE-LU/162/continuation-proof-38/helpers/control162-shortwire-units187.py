"""Append a units erratum; never rewrite a submitted route record or spec."""
import subprocess,shlex

q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');r=b/'route-selection-102/s-ready-cpp-shortwire-source172.json';p=b/'route-selection-102/s-ready-cpp-shortwire-source172-units-correction.json';assert not p.exists()
raw=r.read_bytes();d=json.loads(raw);assert 'HPWL15.59mm versus18.08mm'in d['scope']if'scope'in d else 'HPWL15.59mm versus18.08mm'in d.get('reason','')
p.write_text(json.dumps(dict(time=time.time(),supersedes_text_only=dict(path=str(r),sha256=hashlib.sha256(raw).hexdigest()),correction='The scope/description mistyped the aggregate HPWL units as mm. Actual1700/1702 sums are15592561.605um and18079736.905um, i.e.15.592561605m and18.079736905m. Placement inputs, all queued specifications, constraints and physical evidence are unchanged. Original record retained.'),indent=2)+'\n')
print('Appended unit correction without changing any submitted spec/result')
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
