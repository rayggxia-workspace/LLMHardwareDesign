"""Register both source-identical balanced-placement chains, no predicate change."""
from pathlib import Path
import ast,subprocess,shlex,json
home=Path(r'D:\Data\电路实验');tree=ast.parse((home/'control162-extend-collectors177.py').read_text(encoding='utf-8'));original=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='q'for t in n.targets)))
records=['s-ready-balanced-fast-source172.json','s-ready-balanced-cpp-source172.json'];proof=[]
for record in records:
 q=original.replace('s-ready-fastroute24phase-source172.json',record)
 d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45));assert d['passed'];proof.append(d)
out=home/'control162-collector198-source-proof.json';assert not out.exists();out.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
for name in ['control162-system-ready140.py','control162-final-receipts-retry140.py','control162-next-gate143.py']:
 p=home/name;s=p.read_text(encoding='utf-8');anchor="'s-ready-cpp-weighted-local-source172.json'";assert s.count(anchor)==1
 extra=','.join(repr(r)for r in records);assert all(repr(r)not in s for r in records)
 s=s.replace(anchor,anchor+','+extra);compile(s,name,'exec');p.write_text(s,encoding='utf-8');print(name,'1980/1981 discovered; original joint predicates unchanged')
