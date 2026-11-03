from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-measured-placement-bounds160.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope);q=scope['q']
for a,b in [('source-160','source-161'),('s-ready-measured-placement-bounds160','s-ready-clear-placement-bounds161'),('sready160-measured-placement-native-cap-config','sready161-clear-placement-native-cap-config'),('[1600,1601,1602,1603,1604,1610,1611]','[1620,1621,1622]'),('measured-placement-native-residual-160','clear-placement-native-residual-161'),('measured-placement-native-pin-load-160','clear-placement-native-pin-load-161'),('sready160-measured-native','sready161-clear-native')]:
 assert a in q,a;q=q.replace(a,b)
compile(q,'clear_placement_bounds161','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
