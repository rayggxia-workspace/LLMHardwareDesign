import subprocess,shlex,json,time
from pathlib import Path
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');q=b/'dynamic-03/node5';d=json.loads((q/'queue-state.json').read_text());p=b/'r256-native-warm-regression-973';r=dict(time=time.time(),active=d['active'],finished={k:v for k,v in d['finished'].items()if 'sready973'in k},receipt=None)
if(p/'receipt.json').exists():
 v=json.loads((p/'receipt.json').read_text());r['receipt']=dict(passed=v['passed'],stage=v.get('stage'))
if(p/'directional-regression.json').exists():
 v=json.loads((p/'directional-regression.json').read_text());w=v.get('weighted_bidirectional_cases',{});r['weighted']=dict(passed=w.get('passed'),cases=len(w.get('cases',[])),rejected=len(w.get('rejected',[])),std_heap_replays=sum(x.get('std_heap_route_and_filtered_log_exact_replay')is True for x in w.get('cases',[])),heap_check_counts=sorted(set(x['proof']['distance_oracle'].get('independent_weighted_heap_order_checks',0)for x in w.get('cases',[]))))
f=q/'00-r-sready973-native-warm-regression.log'
if f.exists():
 with f.open('rb')as h:h.seek(0,2);h.seek(max(0,h.tell()-2000));r['log_tail']=h.read().decode(errors='replace')
print(json.dumps(r))
'''
raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]);out=Path(__file__).parent/'control162-read979';out.mkdir(exist_ok=True);(out/(str(time.time_ns())+'.json')).write_bytes(raw);print(raw.decode())

