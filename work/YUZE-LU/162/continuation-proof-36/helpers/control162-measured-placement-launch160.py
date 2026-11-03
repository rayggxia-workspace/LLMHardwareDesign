"""Queue measured-budget searches and an unchanged-default replay first."""
from pathlib import Path
import ast,subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-internal-channel-preflight158.py');q=ast.literal_eval(ast.parse(p.read_text(encoding='utf-8')).body[2].value)
for a,b in [("source=b/'source-157'","source=b/'source-160'"),('fbb61e6fb3e1bb7dbff94d3189c33420fe629690','7a02d7a8eae39733b4c43fcdcdfbb1d95e713df0'),('sready158-internal-channel-preflight','sready160-measured-budget-placement'),('[(3,95098,1432),(6,95101,1433)]','[(3,95098,1444)]'),("for seed,gap in ([(1580,64),(1582,512)]if node==3 else[(1581,256),(1583,1024)]):","for seed,gap in [(1600,64),(1601,256),(1602,512),(1603,1024),(1604,64)]:"),('00-j-sready158-internal-channel-','00-j-sready160-measured-placement-'),("'--seed',seed,'--channel-gap-um'","'--seed',(1580 if seed==1604 else seed),'--channel-gap-um'")]:
 assert a in q,a;q=q.replace(a,b)
anchor="  spec=dict(script='system_upper.py'"
assert anchor in q
q=q.replace(anchor,"  if seed!=1604:a+=['--placement-residual-budget',base/'internal-channel-native-pin-load-158/native-pin-load.json']\n"+anchor)
q=q.replace('Actual large-halo mature routes still hundreds of thousands of shorts; effort50 changes overflow only about3percent. Compare smaller density objective .35 with actual internal gaps64/256/512/1024 while retaining all native masks and209 Link8 rigid offsets. Replace only two verified own duplicate source140 searches; other identical placement controls and all three mature routes continue. No physical gate change, no parent/R/other task changes.',
 'Actual1581/1582/1583 fail2/1/29 high minimum-input/native-cap necessary bounds. New source160 subtracts actual native ground and minimum actual input capacitance in placement search only. Four measured-budget gaps and exact original1580 default seed replay; default replay must reproduce every placement coordinate/terminal and trial metric. Only exact own source140 duplicate1444 retired after all five diagnostics queued; retained1422 controls1491/1494/1497/1500 and all five mature routers continue. Original geometry/PG/RC/300MHz acceptors unchanged, no parent/R/other tasks touched.')
compile(q,'measured_budget_placement160','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
