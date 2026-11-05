import ast,subprocess,shlex
from pathlib import Path
t=ast.parse(Path(r'D:\Data\电路实验\control162-rebalance-probes127.py').read_text())
q=next(ast.literal_eval(n.value)for n in t.body if isinstance(n,ast.Assign)and any(isinstance(a,ast.Name)and a.id=='q'for a in n.targets))
start=q.index('for job,queue,probe,old_names in ');end=q.index(':\n state=',start)
q=q[:start]+"for job,queue,probe,old_names in [(95119,'dynamic-02/node26','00-a00-s1182-final132-physical',['01-c-drive-route-931','01-c-decaying-weight-route-952'])]"+q[end:]
q=q.replace('s-probe-rebalance127','s-final-rebalance133')
q=q.replace('Only exact own superseded original-S upper-route searches on node25/26. Actual32GiB probes rejected by protected memory admission as final S LEC grows toward100GiB. Release minimum old32GiB forecasts under current observed availability. Keep four S, all parent allocations, other six nodes/tasks, immutable specs/logs/results; cancelled searches incomplete not physical failures.', 'Release only minimum exact own superseded external-S-Link8 searches on node26 for actual completed new S1182 final64GiB physical gate. Observed memory admission preserved; no forecast/safety/CPU relaxation. Four S raw results/all current native DRC/functions/other tasks/parent allocations and all immutable specs/logs/results retained. Cancelled old search incomplete, never failed physical evidence.')
compile(q,'actual-final-native-slot','exec')
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
