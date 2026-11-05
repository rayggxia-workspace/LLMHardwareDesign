"""Use the second currently free own slot for independent measured-budget seeds."""
from pathlib import Path
import ast,subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-capacity-launch140.py');q=ast.literal_eval(ast.parse(p.read_text(encoding='utf-8')).body[1].value)
for a,b in [('sready140-capacity-placements1420-1425.json','sready160-measured-placement-refill1610-1611.json'),('[(1420,2,64,.45),(1421,4,256,.45),(1422,2,256,.55),(1423,4,512,.55),(1424,2,256,.65),(1425,4,512,.65)]','[(1610,6,256,.35),(1611,6,512,.35)]'),("b/('dynamic-05/node'+str(node))","b/('dynamic-02/node'+str(node))"),('00-p-sready140-capacity-','00-j-sready160-measured-refill-'),('source-140','source-160'),("'--seed',str(seed)","'--placement-residual-budget',base/'internal-channel-native-pin-load-158/native-pin-load.json','--seed',str(seed)")]:
 assert a in q,a;q=q.replace(a,b)
q=q.replace('Current qualified1391/1404 actual signal HPWL requires 4185403 grid edges across5300768 two-layer nodes, an optimistic79percent occupancy before detours/vias/PG. Preserve four existing exact routes and run more spacious placement diagnostics in free own sixteen-CPU slots. Capacity target changes search objective only, never any acceptance threshold or block masks. Same exact qualified21 types and same actual235instance graph.',
 'Fill actual node6 fourth16CPU slot with two independent measured-budget seeds while node3 executes original four gaps and default replay. Same source160 actual native/pin search objective, all physical gates unchanged. No additional node, no cancellation or modified queued spec, no R/other-task change.')
compile(q,'measured_budget_free_slot_refill160','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
