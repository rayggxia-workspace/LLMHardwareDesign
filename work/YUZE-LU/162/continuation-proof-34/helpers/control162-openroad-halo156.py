"""Queue same qualified search on an existing larger-halo scene, no new node."""
from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-openroad-route156.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope)
q=scope['q']
changes={'s-ready-openroad-source156.json':'s-ready-openroad-halo-source156.json',
 'options=[(1513,2,1,valid[1470])]':'options=[(1514,4,1,valid[1474])]',
 'assert node==2':'assert node==4',"('dynamic-05/node2')":"('dynamic-05/node4')",
 "b/'dynamic-05/node2/queue-state.json'":"b/'dynamic-05/node4/queue-state.json'",
 "len(state['active'])<=3":"len(state['active'])<=4",'95341':'95391','NodeList=node2 ':'NodeList=node4 ',
 'existing1470 exact qualified halo placement':'existing1474 exact qualified larger-halo placement'}
for old,new in changes.items():
 assert old in q,old
 q=q.replace(old,new)
compile(q,'actual_larger_halo_openroad156','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
