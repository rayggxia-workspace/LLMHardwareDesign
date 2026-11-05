import subprocess,shlex
q="""from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');r=b/'r256-composition-453';p=r/'native-sta/receipt.json';d=json.loads(p.read_text());print('native_receipt',json.dumps({k:d[k]for k in ['passed','execution_passed','typed_native_timing_passed','minimum_setup_ns','minimum_hold_ns','native_coverage_passed','scope']if k in d}));print('timing',(r/'native-sta/timing-summary.tsv').read_text())
p=r/'native-sta/native-system-audit.json';d=json.loads(p.read_text());print('native_audit',json.dumps({k:v for k,v in d.items()if not isinstance(v,(list,dict))})[:1200])
d=json.loads((r/'native-pin-load/native-pin-load.json').read_text());print('initial_necessary',[(x['placement'],x['violations'])for x in d['placements']])
for seed in [4610,4611]:
 for folder in [r/'cap-candidates'/str(seed),r/'cap-necessary-461'/str(seed)/'native-pin-load']:
  p=folder/'receipt.json'
  if p.exists():
   d=json.loads(p.read_text());print(seed,folder.name,'passed',d['passed'])
  p=folder/'native-pin-load.json'
  if p.exists():
   d=json.loads(p.read_text());print(seed,'violations',[x['violations']for x in d['placements']])
for folder in ['dynamic-05/node2','dynamic-05/node4','dynamic-04/node25']:
 d=json.loads((b/folder/'queue-state.json').read_text());print(folder,'active',d['active'])
"""
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
