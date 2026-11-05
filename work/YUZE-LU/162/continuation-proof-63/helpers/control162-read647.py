import subprocess,shlex
code=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');d=json.loads((b/'r256-directional-bidir-regression-635/directional-regression.json').read_text());m=d['directional_bidirectional_cases'];assert d['passed']and m['passed']and len(m['cases'])==18
exact=[x for x in m['cases']if x['cost']==2];assert len(exact)==6 and all(x['original_cost2_route_and_log_exact']for x in exact)
assert all(x['proof']['distance_oracle']['independent_bidirectional_dijkstra_checks']==100 and x['proof']['distance_oracle']['independent_directional_bidirectional_dijkstra_checks']==200 and x['proof']['final_conflicts']==0 for x in m['cases'])
print(json.dumps(dict(passed=True,new_actual_cases=len(m['cases']),exact_original_cost2_replays=len(exact),original_dijkstra=100,added_directional_dijkstra=200,original_rejected=len(d['rejected']),actual_bidir_branches={str(cost):sum(x['actual_bidirectional_branches']for x in m['cases']if x['cost']==cost)for cost in [2,8,32]},whole_system_qualified=False)))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],universal_newlines=True))
