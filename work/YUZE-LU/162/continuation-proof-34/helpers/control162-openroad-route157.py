"""Admit actual 50-iteration CUGR search only after executed matching probes."""
from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-openroad-route156.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope)
q=scope['q']
changes={"source=b/'source-156'":"source=b/'source-157'","source='source-156'":"source='source-157'",
 's-ready-openroad-source156.json':'s-ready-openroad-source157.json',
 'router-openroad-preflight-156':'router-openroad-effort-preflight-157',
 'options=[(1513,2,1,valid[1470])]':'options=[(1515,4,1,valid[1474])]',
 'assert node==2':'assert node==4',"('dynamic-05/node2')":"('dynamic-05/node4')",
 "b/'dynamic-05/node2/queue-state.json'":"b/'dynamic-05/node4/queue-state.json'",
 '95341':'95391','NodeList=node2 ':'NodeList=node4 ',
 "'--router','openroad'":"'--router','openroad','--openroad-congestion-iterations',50",
 "proof['passed']and proof['independent_grid_verification_passed']":"proof['passed']and proof['congestion_iterations']==50 and proof['independent_grid_verification_passed']",
 'sready156openroad-':'sready157openroad-',
 'existing1470 exact qualified halo placement':'existing1474 exact qualified larger-halo placement with50 CUGR search iterations'}
for old,new in changes.items():
 assert old in q,old
 q=q.replace(old,new)
compile(q,'actual_cugr50_route157','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
