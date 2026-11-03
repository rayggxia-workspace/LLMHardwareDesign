import subprocess,shlex
q=r'''from pathlib import Path
import json
c=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-ready-composition-01/1391')
for folder,file,key in [('local-density-native-residual-165','native-cap-residual.json','optimistic_total_ff'),('local-density-native-pin-load-165','native-pin-load.json','optimistic_total_with_minimum_pin_ff')]:
 p=c/folder/file
 if not p.exists():print(folder,'unfinished');continue
 for r in json.loads(p.read_text())['placements']:
  worst=max(r['rows'],key=lambda d:d[key]['high']/d['max_capacitance_ff']);print(folder,Path(r['placement']).name,r['violations'],'worst_high_ratio',worst[key]['high']/worst['max_capacitance_ff'])
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
