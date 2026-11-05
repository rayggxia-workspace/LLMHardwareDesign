import subprocess,shlex,json,time
from pathlib import Path
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');g=json.loads((b/'r256-composition-453/topology/boundary-graph.json').read_text());p=json.loads((b/'r256-composition-453/cap-candidates/5380/placement.json').read_text());rows=[]
for name in ['11162','11166','11164','11422','7942','2']:
 c=g['connections'][name];rows.append(dict(net='net_'+name,connection=c))
print(json.dumps(dict(time=time.time(),rows=rows)))
'''
raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]);d=json.loads(raw);out=Path(__file__).parent/'control162-trace730.json';assert not out.exists();out.write_bytes(raw);print(json.dumps([dict(net=r['net'],driver=r['connection']['driver'],sink_count=len(r['connection']['sinks']),sample_sink=r['connection']['sinks'][:1])for r in d['rows']]))
