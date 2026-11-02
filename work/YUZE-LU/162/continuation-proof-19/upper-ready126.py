import ast,subprocess,shlex
from pathlib import Path
tree=ast.parse(Path(r'D:\Data\电路实验\control162-S-upper-ready121.py').read_text(encoding='utf-8'))
original=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='q'for t in n.targets))
for candidate,route_base in [(1260,1270),(1261,1280)]:
 q=original.replace('1182',str(candidate)).replace('source-121','source-126').replace('source121','source126').replace('s-internal-qualified-02','s-reset-qualified-01').replace('s-internal-composition-01','s-reset-composition-01')
 for i in range(4):q=q.replace(str(1230+i),str(route_base+i))
 q=q.replace("record=b/'route-selection-102/", "record=b/'route-selection-102/")
 q=q.replace(";assert not record.exists()", "\nif record.exists():print('Already appended:',record);raise SystemExit(0)")
 print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
