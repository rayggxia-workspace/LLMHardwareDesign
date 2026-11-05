"""Discover the exact new C++ placement record, preserving all joint predicates."""
from pathlib import Path
import ast,subprocess,shlex,json

home=Path(r'D:\Data\电路实验');p=home/'control162-extend-collectors177.py'
tree=ast.parse(p.read_text(encoding='utf-8'))
q=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='q'for t in n.targets)))
assert 's-ready-fastroute24phase-source172.json'in q
q=q.replace('s-ready-fastroute24phase-source172.json','s-ready-cpp-localdensity-source172.json')
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45));assert d['passed']
out=home/'control162-collector185-source-proof.json';assert not out.exists();out.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
for name in ['control162-system-ready140.py','control162-final-receipts-retry140.py','control162-next-gate143.py']:
    p=home/name;s=p.read_text(encoding='utf-8');old="'s-ready-fastroute24phase-source172.json'";new="'s-ready-cpp-localdensity-source172.json'"
    assert s.count(old)==1 and new not in s;s=s.replace(old,old+','+new)
    compile(s,name,'exec');p.write_text(s,encoding='utf-8');print(name,'exact1850 discovery; all original joint acceptance predicates unchanged')
