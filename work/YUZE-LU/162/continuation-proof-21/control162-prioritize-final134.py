import ast,subprocess,shlex
from pathlib import Path
t=ast.parse(Path(r'D:\Data\电路实验\control162-rebalance-probes127.py').read_text())
q=next(ast.literal_eval(n.value)for n in t.body if isinstance(n,ast.Assign)and any(isinstance(a,ast.Name)and a.id=='q'for a in n.targets))
start=q.index('for job,queue,probe,old_names in ');end=q.index(':\n state=',start)
q=q[:start]+"for job,queue,probe,old_names in [(95098,'dynamic-02/node3','00-a00-s1180-final133-physical',['01-c-capacity-route-1121'])]"+q[end:]
start=q.index(";rows=[r for r in state['memory_admissions']");end=q.index('\n details=',start)
q=q[:start]+"\n assert probe in state['unfinished'];assert len(state['active'])==state['slots']==4\n admission=dict(forecast_gib=0,available_bytes=0,reason='Four c64 slots full; prioritize actual new S1180 final gate over one own obsolete external-S-Link8 graph search');count=1"+q[end:]
q=q.replace('s-probe-rebalance127','s-final-priority134-node3')
q=q.replace("((admission['forecast_gib']-32*count)*1.2+16)*1024**3","None")
q=q.replace('Only exact own superseded original-S upper-route searches on node25/26. Actual32GiB probes rejected by protected memory admission as final S LEC grows toward100GiB. Release minimum old32GiB forecasts under current observed availability. Keep four S, all parent allocations, other six nodes/tasks, immutable specs/logs/results; cancelled searches incomplete not physical failures.', 'Only one exact own superseded old-S-Link8 search1121 on node3 stopped to prioritize actual S1180 final physical evidence. Other two searches and complete native DRC retained, other7allocations/tasks unchanged, all immutable specs/logs/results preserved; cancelled search incomplete. No gate or memory rule changed.')
compile(q,'exact-own-final-priority','exec')
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
