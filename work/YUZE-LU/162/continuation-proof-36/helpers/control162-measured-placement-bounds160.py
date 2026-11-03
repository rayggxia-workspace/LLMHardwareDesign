"""Append actual lower-bound stages for every measured search and replay."""
from pathlib import Path
import ast,subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-internal-channel-bounds158.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope);q=scope['q']
for a,b in [('source-157','source-160'),('s-ready-internal-channel-bounds158','s-ready-measured-placement-bounds160'),('sready158-internal-channel-native-cap-config','sready160-measured-placement-native-cap-config'),('[1580,1581,1582,1583]','[1600,1601,1602,1603,1604,1610,1611]'),('internal-channel-native-residual-158','measured-placement-native-residual-160'),('internal-channel-native-pin-load-158','measured-placement-native-pin-load-160'),('sready158-internal-native','sready160-measured-native')]:
 assert a in q,a;q=q.replace(a,b)
q=q.replace('four actual internal-channel placements','seven actual measured-budget placements/default replay')
compile(q,'measured_placement_bounds160','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
