from pathlib import Path
import subprocess,shlex,json,time
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');q=b/'dynamic-03/node5';s=json.loads((q/'queue-state.json').read_text());p=b/'r256-native-prefix-path-diagnostic-873';r=dict(time=time.time(),active=s['active'],finished=s['finished'].get('00-m-sready873-native-prefix-path-diagnostic'),receipt=None,cases_done=len(list((p/'native-prefix').glob('case-*/diagnostic.json'))))
if(p/'receipt.json').exists():r['receipt']=json.loads((p/'receipt.json').read_text())
f=q/'00-m-sready873-native-prefix-path-diagnostic.log'
if f.exists():r['log_tail']=f.read_text()[-2300:]
print(json.dumps(r))
'''
raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]);h=Path(__file__).parent/'control162-read878';h.mkdir(exist_ok=True);(h/(str(time.time_ns())+'.json')).write_bytes(raw);d=json.loads(raw);v=d.get('receipt');d['receipt']=dict(passed=v['passed'],stage=v.get('stage'),error=v.get('error'))if v else None;print(json.dumps(d))
