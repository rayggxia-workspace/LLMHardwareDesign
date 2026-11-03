import ast,subprocess,shlex
from pathlib import Path
module=ast.parse(Path(r'D:\Data\电路实验\control162-retire385.py').read_text(encoding='utf-8'))
q=ast.literal_eval(next(n.value for n in module.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='q'for t in n.targets)))
pairs=[('sready385-current-scene-refill','sready390-measured-budget-refill'),('sready384-directional/tasks.json','sready389-measured-route-budget/tasks.json'),("len(tasks['tasks'])==15","len(tasks['tasks'])==14"),("[(5,95155,'dynamic-03/node5',1480),(25,95204,'dynamic-04/node25',1501)]","[(2,95341,'dynamic-05/node2',1430),(3,95098,'dynamic-02/node3',2230)]"),("source.name in ['source-142','source-143']","re.fullmatch('source-[0-9]+',source.name)and(source/'source-manifest.json').is_file()"),('current345instance reset53 directional comparisons','current345instance reset53 measured-native/input-budget full searches')]
for old,new in pairs:
 assert old in q,old;q=q.replace(old,new)
compile(q,'retire390','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
