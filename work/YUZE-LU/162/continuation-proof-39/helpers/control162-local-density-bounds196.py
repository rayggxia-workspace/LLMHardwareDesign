"""Queue original native-ground/input-pin necessary checks for new placements."""
from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-local-density-bounds165.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope)
q=scope['q']
for a,b in [('source-165','source-196'),('s-ready-local-density-bounds165','s-ready-strong-local-bounds196'),('sready165-local-density-native-cap-config','sready196-strong-local-native-cap-config'),('[1700,1701,1702,1703,1704]','[1960,1961,1962]'),('local-density-native-residual-165','strong-local-native-residual-196'),('local-density-native-pin-load-165','strong-local-native-pin-load-196'),('sready165-local-density-native','sready196-strong-local-native')]:
 assert a in q,a
 q=q.replace(a,b)
compile(q,'strong_local_necessary_bounds196','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
