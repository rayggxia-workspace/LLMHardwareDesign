"""Discover both exact weighted-placement records, unchanged joint predicates."""
from pathlib import Path
import ast,subprocess,shlex,json

home=Path(r'D:\Data\电路实验');p=home/'control162-extend-collectors177.py';tree=ast.parse(p.read_text(encoding='utf-8'))
q=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='q'for t in n.targets)))
q=q.replace('s-ready-fastroute24phase-source172.json','s-ready-cpp-weighted-local-source172.json').replace("len(d['tasks'])==7","len(d['tasks'])==14")
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45));assert d['passed']
out=home/'control162-collector194-source-proof.json';assert not out.exists();out.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
for name in ['control162-system-ready140.py','control162-final-receipts-retry140.py','control162-next-gate143.py']:
    p=home/name;s=p.read_text(encoding='utf-8');old="'s-ready-cpp-shortwire-source172.json'";new="'s-ready-cpp-weighted-local-source172.json'"
    assert s.count(old)==1 and new not in s;s=s.replace(old,old+','+new)
    compile(s,name,'exec');p.write_text(s,encoding='utf-8');print(name,'exact1852/1853 discovery; original joint acceptance unchanged')
