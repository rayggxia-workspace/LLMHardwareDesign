import ast,subprocess,shlex
from pathlib import Path
t=ast.parse(Path(r'D:\Data\电路实验\control162-queue-escape133.py').read_text())
q=next(ast.literal_eval(n.value)for n in t.body if isinstance(n,ast.Assign)and any(isinstance(a,ast.Name)and a.id=='q'for a in n.targets))
q=q.replace('source-133','source-135').replace('source133','source135').replace('1330','1350')
q=q.replace("failed,'--physical']", "failed,'--s-escape-checkpoint',b/'s-escape-repair-01/candidate-1340','--physical']")
q=q.replace('four M10 same-net spacing failures only.', 'four M10 same-net spacing failures; exact1340 vertical-L geometry passed whole native DRC but overnarrow dry-run format guard failed. Reuse only exact zero-DRC preparation, fresh final RC and every independent gate still mandatory.')
compile(q,'actual-zero-drc-S-resume','exec')
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
