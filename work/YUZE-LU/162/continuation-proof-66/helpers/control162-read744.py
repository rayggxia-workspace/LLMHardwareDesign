import subprocess,shlex,json,time
from pathlib import Path
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');q=b/'dynamic-05/node4';d=json.loads((q/'queue-state.json').read_text());p=b/'r256-pair-window-regression-736';r=dict(time=time.time(),active=d['active'],finished={k:v for k,v in d['finished'].items()if 'sready736'in k},receipt=None)
if(p/'receipt.json').exists():
 v=json.loads((p/'receipt.json').read_text());r['receipt']=dict(passed=v['passed'],stage=v.get('stage'))
if(p/'directional-regression.json').exists():
 v=json.loads((p/'directional-regression.json').read_text());w=v.get('weighted_bidirectional_cases',{});r['weighted']=dict(passed=w.get('passed'),cases=len(w.get('cases',[])),rejected=len(w.get('rejected',[])))
f=q/'00-f-sready736-pair-window-regression.log'
if f.exists():
 with f.open('rb')as h:h.seek(0,2);h.seek(max(0,h.tell()-2000));r['log_tail']=h.read().decode(errors='replace')
print(json.dumps(r))
'''
raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]);out=Path(__file__).parent/'control162-read744';out.mkdir(exist_ok=True);(out/(str(time.time_ns())+'.json')).write_bytes(raw);print(raw.decode())
