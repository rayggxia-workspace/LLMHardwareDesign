import subprocess,shlex
q=r'''from pathlib import Path
import json,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');d=json.loads((b/'r256-search-phase-analysis-498/receipt.json').read_text());print('stops',dict(collections.Counter(x['last']['net']for x in d['stops'])))
for row in d['actual_graph_nets']:
 print(json.dumps(dict(net=row['net'],driver=row.get('driver'),sink_count=row.get('sink_count'),sinks=row.get('sinks',[])[:3],kind=row.get('kind'))))
p=b/'r256-search-phase-profile-494/receipt.json';r=json.loads(p.read_text());print('outer',r['passed'],r['stage']);r=json.loads((p.parent/'profile/receipt.json').read_text());print('all16exact',len(r['trials']),all(x['exact_original_first7round_prefix']for x in r['trials']))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
