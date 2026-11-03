"""Summarize actual complete-case evidence without rereading huge path dumps."""
import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');folder=b/'router-complete-path-full-205/complete-paths'
g=json.loads((b/'s-ready-composition-01/1391/topology/boundary-graph.json').read_text())
files=sorted(folder.glob('case-*/diagnostic.json'));print('Verified complete cases',len(files),'of16')
if files:
 p=next((p for p in files if p.parent.name=='case-0'),files[0]);d=json.loads(p.read_text())
 print(json.dumps({k:v for k,v in d.items()if k not in ['top_nets','top_tiles']}))
 print('Actual hottest tiles',json.dumps(d['top_tiles'][:8]))
 for row in d['top_nets'][:12]:
  n=row['net'];c=g['connections'].get(n[4:]);row['driver']=c['driver']if c else n
  row['sink_count']=len(c['sinks'])if c else 235;print(json.dumps(row))
r=folder.parent/'receipt.json';print('Whole diagnostic execution',json.loads(r.read_text())['passed']if r.exists()else 'unfinished')
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=35).decode())
