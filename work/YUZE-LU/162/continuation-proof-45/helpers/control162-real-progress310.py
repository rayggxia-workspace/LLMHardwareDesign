import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
p=b/'r256-composition-273/function';d=json.loads((p/'receipt.json').read_text());print('function',{k:v for k,v in d.items()if k in ['passed','real_program_count','actual_final_leaf_count','physical_instances','R_integrated']})
for x in p.glob('initial-*.json'):print(x.name,x.read_text()[:900])
p=b/'r256-composition-274/native-pin-load307/native-pin-load.json';d=json.loads(p.read_text());print('native pin necessary',[(row['placement'],row['violations'],max(max(v['optimistic_total_with_minimum_pin_ff'].values())/v['max_capacitance_ff']for v in row['rows']))for row in d['placements']])
r=json.loads((b/'route-selection-102/sready267-r256-upper/tasks.json').read_text());print('dispatched',len(r['tasks']),'placement',r['selected_placement'],'source roots',sorted(set(row['spec']['source_root']for row in r['tasks'])));print('route queues',[row['path']for row in r['tasks']if row['spec']['script']=='system_upper.py'])
'''
compile(q,'cprogress284','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
