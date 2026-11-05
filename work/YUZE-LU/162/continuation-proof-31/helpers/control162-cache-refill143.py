"""Queue the current S implementation in slots occupied by old external-S searches."""
from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-cache-route143.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope)
q=scope['q'].replace('s-ready-cache-source143.json','s-ready-cache-refill-source143.json')
old='options=[(1490,5,4,valid[1470])]'
new='options=[(seed,node,weight,valid[n])for seed,node,weight,n in [(1491,3,1,1470),(1492,3,4,1473),(1493,6,1,1470),(1494,6,1,1473),(1495,6,1,1474),(1496,7,4,1470),(1497,7,4,1473),(1498,7,4,1474),(1499,25,1,1470),(1500,25,1,1473),(1501,25,1,1474),(1502,26,4,1470)]]'
assert old in q;q=q.replace(old,new)
q=q.replace('assert node==5','assert node in (3,6,7,25,26)').replace("('dynamic-03/node5')","(('dynamic-04/'if node==25 else'dynamic-02/')+'node'+str(node))")
q=q.replace('Actual externally expanded halo scenes with all native relative placements fixed;',
            'Twelve independent current235-graph routes queued for exact own slots still occupied by obsolete335 external-S searches; original jobs/results preserved, replacement verified separately. Same actual externally expanded halo scenes with all native relative placements fixed;')
compile(q,'current_hardware_refill_only','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
