from pathlib import Path
import ast
h=Path(__file__).parent;s=(h/'control162-read914.py').read_text(encoding='utf-8');m=ast.parse(s);q=ast.literal_eval(next(x.value for x in m.body if isinstance(x,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='q'for t in x.targets)))
q=q.replace('admission-914','admission-931').replace("[(97097,'dynamic-08/node6',[8860]),(95155,'dynamic-03/node5',[8861,8862])]","[(97097,'dynamic-08/node6',[8590]),(95155,'dynamic-03/node5',[9063])]").replace('assert len(rows)==3','assert len(rows)==2')
q=q.replace(";assert not out.exists();out.mkdir();rows=[];nodes=[]", "\nif out.exists():\n assert out.parent==b and not any(out.iterdir());saved=b/'r256-native-batch-admission-931-incomplete-01';assert not saved.exists();out.rename(saved)\nassert not out.exists();out.mkdir();rows=[];nodes=[]")
assert '[8590]'in q and '[9063]'in q
code='import subprocess,shlex\nq='+repr(q)+"\nprint(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())\n";compile(code,'read931fixed','exec');(h/'control162-read931.py').write_bytes(code.encode())
