import ast,subprocess,shlex
from pathlib import Path
t=ast.parse(Path(r'D:\Data\电路实验\control162-S-upper-ready121.py').read_text())
q=next(ast.literal_eval(n.value)for n in t.body if isinstance(n,ast.Assign)and any(isinstance(a,ast.Name)and a.id=='q'for a in n.targets))
q=q.replace('1182','1350').replace('source-121','source-137').replace('source121','source137')
q=q.replace('s-internal-qualified-02','s-escape-qualified-03').replace('s-internal-composition-01','s-escape-composition-03')
for i in range(4):q=q.replace(str(1230+i),str(1380+i))
q=q.replace(';assert not record.exists()',"\nif record.exists():print('Already appended:',record);raise SystemExit(0)")
compile(q,'same-S-actual-parallel-PG-upper','exec')
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
