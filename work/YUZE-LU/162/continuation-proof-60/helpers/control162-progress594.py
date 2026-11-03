from pathlib import Path
import subprocess,shlex
code=r'''from pathlib import Path
import json,statistics,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');r=json.loads((b/'r256-zero-pattern-regression-589/directional-regression.json').read_text());p=r['ordinary_zero_pattern_cases']
print('actual_regression',json.dumps(dict(passed=r['passed'],unit=p['unit'],pattern_cases=len(p['cases']),pattern_hits=sum(x['zero_pattern_hits']for c in p['cases']for x in c['ordinary_zero_pattern_trace']),actual_fallbacks=p['actual_fallbacks'],new_rejects=len(p['rejected']),legacy_rejects=len(r['rejected']),exact_disabled=p['disabled_bidirectional_default_replay_exact'])))
for seed in [5640,5890]:
 out=b/'r256-composition-453/upper-candidates'/str(seed);progress=[];rounds={};patterns=[];fails=[]
 for p in(out/'route').glob('trial-*/router.log'):
  last={}
  for line in p.read_text().splitlines():
   if not line.startswith('{'):continue
   d=json.loads(line)
   if 'routed'in d:last=d
   if 'conflict_nodes'in d:rounds.setdefault(d['round'],[]).append(d['excess_occupancy'])
   if 'zero_pattern_hits'in d:patterns.append(d)
  if last:progress.append((last['round'],last['routed']))
 print('route',json.dumps(dict(candidate=seed,progress=[min(progress),max(progress)]if progress else[],rounds={k:dict(trials=len(v),mean_excess=statistics.mean(v))for k,v in rounds.items()},pattern_round_records=len(patterns),pattern_hits=sum(x['zero_pattern_hits']for x in patterns),pattern_fallbacks=sum(x['zero_pattern_fallbacks']for x in patterns),receipts=[dict(path=str(p),passed=json.loads(p.read_text()).get('passed'))for p in out.glob('*/receipt.json')],whole_system_qualified=False)))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],universal_newlines=True))
