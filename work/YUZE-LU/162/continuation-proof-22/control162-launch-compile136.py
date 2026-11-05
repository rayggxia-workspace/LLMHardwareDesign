import ast,subprocess,shlex
from pathlib import Path
t=ast.parse(Path(r'D:\Data\电路实验\control162-launch-escape133.py').read_text())
q=next(ast.literal_eval(n.value)for n in t.body if isinstance(n,ast.Assign)and any(isinstance(a,ast.Name)and a.id=='q'for a in n.targets))
q=q.replace('source-133','source-136').replace('s-escape-repair-source133.json','s-compile-parallel-source136.json')
q=q.replace('node=2;oldjob=95097','node=4;oldjob=95099').replace('node2','node4').replace('mix2','mix4').replace('smem2','smem4').replace('s-escape-memory133-node2','s-compile-memory136-node4')
q=q.replace("for count in [48,64]:assert (b/('s-reset-probe-06/'+str(count))/'receipt.json').exists()", "sealed=b/'s-escape-gates-01/1350/sealed/receipt.json'\nif not sealed.exists()or not json.loads(sealed.read_text()).get('passed'):print(json.dumps(dict(ready=False,reason='Actual newS1350 final seal not passed yet; no old allocation changed.')));raise SystemExit(0)")
q=q.replace('s-escape-memory133-node4','s-compile-memory136-node4')
q=q.replace('Only this own c64 allocation is replaced after both diagnostic probes closed. Retire obsolete external-S-Link8 composition searches on this allocation, preserve all evidence and other7allocations. Actual native S LEC peaked145GiB; fresh final report/strict LEC budget256GiB, memory rule unchanged,16CPU and4dynamic slots.', 'Only this own c64 old external-S-Link8 search allocation is replaced once actual S1350 seal passes and new function is ready. Keep other7allocations and every native physical/DRC/old function task. Run supported ungrouped exact-view function and existing parallel formal with128/256GiB budgets, same memory protection and16CPU/four dynamic slots. Final formal still waits for actual successful three-initial function receipt; no gate waiver.')
compile(q,'ready-only-own-compile-controller','exec')
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
