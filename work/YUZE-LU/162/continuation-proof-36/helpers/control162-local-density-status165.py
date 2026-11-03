import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391/cap-capacity-candidates'
for node in [3,6]:
 queue=b/'dynamic-02'/('node'+str(node));d=json.loads((queue/'queue-state.json').read_text());print('node',node,d['active'])
for seed in range(1700,1705):
 p=c/str(seed);r=p/'receipt.json'
 if not r.exists():print(seed,'unfinished','completed_trials',len(list(p.glob('electrical-placement-*.txt'))));continue
 d=json.loads(r.read_text());print(seed,'execution',d.get('passed'),'stage',d.get('stage'))
 if not d['passed']:
  node=3 if seed in [1700,1701,1704]else 6;log=b/'dynamic-02'/('node'+str(node))/('00-j-sready165-local-density-'+str(seed)+'.log');print(log.read_text()[-1800:]);continue
 d=json.loads((p/'placement-search.json').read_text())['electrical_refinement'];rows=d['independent_trials'];selected=next(row for row in rows if row['seed']==d['selected_seed']);print('weight',d['local_density_weight'],'independent_oracles',sum(row['independent_cost_and_nonoverlap_verified']for row in rows),'clear_trials',sum(row['metrics'][5]==0 for row in rows),'metrics',selected['metrics'])
'''
compile(q,'local_density_status165','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
