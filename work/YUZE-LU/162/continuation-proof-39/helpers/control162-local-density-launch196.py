"""Two stronger local-cost probes, exact default replay, own child refill only."""
from pathlib import Path
import ast,subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-internal-channel-preflight158.py')
q=ast.literal_eval(ast.parse(p.read_text(encoding='utf-8')).body[2].value)
replacements=[
 ("source=b/'source-157'","source=b/'source-196'"),
 ('fbb61e6fb3e1bb7dbff94d3189c33420fe629690','1f553be74f4f42844305b28bff011be44d57a030'),
 ('sready158-internal-channel-preflight','sready196-strong-local-placement'),
 ('[(3,95098,1432),(6,95101,1433)]','[(3,95098,1590),(6,95101,1591)]'),
 ("name='00-k-sready140-route-'","name='00-k-sready159internal-route-'"),
 ("b/'source-140'","b/'source-157'"),
 ('source-140/project/experiments','source-157/project/experiments'),
 ("log=Path(out)/'trial-0/router.log'","log=Path(out)/'openroad-search/case-0/openroad.log'"),
 ('for seed,gap in ([(1580,64),(1582,512)]if node==3 else[(1581,256),(1583,1024)]):',
  'for seed,gap in ([(1960,64),(1962,64)]if node==3 else[(1961,64)]):'),
 ('00-j-sready158-internal-channel-','00-j-sready196-strong-local-'),
 ("'--seed',seed,'--channel-gap-um'","'--seed',(1580 if seed==1962 else seed),'--channel-gap-um'")]
for a,b in replacements:
 assert a in q,a
 q=q.replace(a,b)
anchor="  spec=dict(script='system_upper.py'"
assert anchor in q
q=q.replace(anchor,"  if seed!=1962:a+=['--placement-residual-budget',base/'internal-channel-native-pin-load-158/native-pin-load.json','--placement-local-density-weight',('1000000000' if seed==1960 else '10000000000')]\n"+anchor)
old='Actual large-halo mature routes still hundreds of thousands of shorts; effort50 changes overflow only about3percent. Compare smaller density objective .35 with actual internal gaps64/256/512/1024 while retaining all native masks and209 Link8 rigid offsets. Replace only two verified own duplicate source140 searches; other identical placement controls and all three mature routes continue. No physical gate change, no parent/R/other task changes.'
new='Actual1770 global overflow116814 despite66.87percent total utilization;1702 local-density peak2.36207 at1e8 weight. Test two higher placement-only penalties1e9/1e10 and exact original1580 default replay. Independent Python cost/nonoverlap oracle and original measured necessary budgets retained; no native mask/RTL/final acceptor change. Queue replacements first, then retire only two verified own older1580-placement search children1590/1591; preserve specs/partial evidence and other controls/parents/R/foreign work. Same eight nodes and16CPU slots, unchanged memory admission guard. Incomplete search retirement, not final physical failure.'
assert old in q
q=q.replace(old,new)
compile(q,'strong_local_placement196','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
