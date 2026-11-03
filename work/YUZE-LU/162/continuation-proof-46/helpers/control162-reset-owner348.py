import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-274';g=json.loads((root/'topology/boundary-graph.json').read_text());d=json.loads((b/'r256-native-tree-cap-diagnostic-347/summary.json').read_text())
for n in ['net_8915','net_8280']:
 c=g['connections'][n[4:]];print(n,'driver',c['driver'],'sinks',len(c['sinks']),[r['instance']for r in c['sinks']][:7]);print('mincap',next(r for r in d['placements'][0]['rows']if r['net']==n));w=json.loads((root/'cap-candidates/3070/wire-cap-lower-bound.json').read_text());print('actualdriver',next(r['physical_driver']for r in w['rows']if r['net']==n))
'''
print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
