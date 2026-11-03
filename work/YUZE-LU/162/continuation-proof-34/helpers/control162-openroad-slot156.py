"""Free one exact own duplicate only after its replacement seven gates exist."""
from pathlib import Path
import subprocess,shlex,ast
p=Path(r'D:\Data\电路实验\control162-regression-launch142.py');q=ast.literal_eval(ast.parse(p.read_text()).body[1].value)
start=q.index("subprocess.run(['scancel'");q=q[:start]+q[start:q.index("p=queue/'pending",start)]+"print('Retired verified own duplicate only',targets[0]['step'])\n"
changes={"source=b/'source-142'":"source=b/'source-156'",'415069fbe00e9706eee8bfcfeec842ec4b0ac878':'61763aaf30cf3a5f612f4a4f28efbb3fa6f51ff2',
 'sready142-independent-congestion-regression':'sready156-duplicate1452-retired','1411':'1452','1410':'1450',"+1]=='4'":"+1]=='1'",
 'Retire one exact own slow coupled-weight4 ordering search to admit full default-plus-new search-order regression; preserve all old evidence, other search controls, parent allocations and physical gates. Not a completed physical failure.':
 'Only verified own duplicate original weight1 search1452, same1424 placement as retained1450/1451/1453/1433/1445/1449. Exact-source156 actual mature route1514 on previously passed1474 larger-halo scene plus all six unchanged full gates queued first. Preserve all parent allocations, old specs/partial evidence, other searches/tasks and R. No new node, no physical acceptance change; unfinished search retirement, not physical failure.'}
for old,new in changes.items():
 assert old in q,old
 q=q.replace(old,new)
anchor="queue=b/'dynamic-05/node4';"
insert="new=json.loads((b/'route-selection-102/s-ready-openroad-halo-source156.json').read_text());assert len(new['tasks'])==7 and new['source']=='source-156'\nfor row in new['tasks']:assert sha(row['path'])==row['sha256']\n"
assert anchor in q;q=q.replace(anchor,insert+anchor)
compile(q,'exact_duplicate_step_retirement156','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
