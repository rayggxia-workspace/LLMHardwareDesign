import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391'
for f in ['internal-channel-native-residual-158/native-cap-residual.json','internal-channel-native-pin-load-158/native-pin-load.json']:
 p=c/f
 if not p.exists():print(f,'unfinished');continue
 d=json.loads(p.read_text());print(f,'execution',d.get('passed'))
 for r in d['placements']:
  print(Path(r['placement']).name,'violations',r['violations'])
  rows=r['rows'];print('worst',max(rows,key=lambda r:r.get('optimistic_total_ff',{}).get('high',0)/r.get('max_capacitance_ff',1)))
for node in [3,6]:
 p=b/'dynamic-02'/('node'+str(node));d=json.loads((p/'queue-state.json').read_text());print('node',node,d['active'])
 for f in (p/'results').glob('*sready158*.json'):print(f.name,json.loads(f.read_text()))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
