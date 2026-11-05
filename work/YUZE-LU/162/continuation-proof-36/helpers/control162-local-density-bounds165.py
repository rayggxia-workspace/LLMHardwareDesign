from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-measured-placement-bounds160.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope);q=scope['q']
for a,b in [('source-160','source-165'),('s-ready-measured-placement-bounds160','s-ready-local-density-bounds165'),('sready160-measured-placement-native-cap-config','sready165-local-density-native-cap-config'),('[1600,1601,1602,1603,1604,1610,1611]','[1700,1701,1702,1703,1704]'),('measured-placement-native-residual-160','local-density-native-residual-165'),('measured-placement-native-pin-load-160','local-density-native-pin-load-165'),('sready160-measured-native','sready165-local-density-native')]:
 assert a in q,a;q=q.replace(a,b)
compile(q,'local_density_necessary_bound165','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
