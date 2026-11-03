"""Discover exactly21 source213 tasks after unchanged acceptance SHA proof."""
from pathlib import Path
import ast,subprocess,shlex,json
home=Path(r'D:\Data\电路实验');tree=ast.parse((home/'control162-extend-collectors177.py').read_text(encoding='utf-8'));q=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='q'for t in n.targets)))
q=q.replace('source-172','source-213').replace('s-ready-fastroute24phase-source172.json','s-ready-initial-order-source213.json').replace("len(d['tasks'])==7","len(d['tasks'])==21")
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45));assert d['passed']
out=home/'control162-collector215-source-proof.json';assert not out.exists();out.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
for name in ['control162-system-ready140.py','control162-final-receipts-retry140.py','control162-next-gate143.py']:
 p=home/name;s=p.read_text(encoding='utf-8');old="'s-ready-exact-cpp-source172.json'";new="'s-ready-initial-order-source213.json'";assert s.count(old)==1 and new not in s;s=s.replace(old,old+','+new)
 if name!='control162-next-gate143.py':
  old="'source-157','source-172']";assert s.count(old)==1;s=s.replace(old,"'source-157','source-172','source-213']")
 compile(s,name,'exec');p.write_text(s,encoding='utf-8');print(name,'2150/2151/2152 discovered; eight final acceptors and joint predicate unchanged')
