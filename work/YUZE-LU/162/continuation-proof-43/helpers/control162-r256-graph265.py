import subprocess,shlex
q=r'''from pathlib import Path
import json,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');g=json.loads((b/'r256-composition-259/topology/boundary-graph.json').read_text());links=g['boundary_links']['links'];print('link groups',dict(collections.Counter(r['source_instance']for r in links)))
for bit,c in sorted(g['connections'].items(),key=lambda kv:-len(kv[1]['sinks']))[:10]:print('fanout',bit,c['driver'],len(c['sinks']))
p=b/'r256-fixed-pg-257/wrapper/complete-checker/native-complete/receipt.json';d=json.loads(p.read_text());print('R whole native check', {k:v for k,v in d.items()if k not in ['commands','inputs','outputs','artifacts','native_paths']})
'''
compile(q,'graph265','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
