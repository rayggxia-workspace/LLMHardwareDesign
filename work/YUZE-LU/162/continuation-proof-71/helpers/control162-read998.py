from pathlib import Path
import subprocess,shlex,json,time
q='''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');rows=[]
for tag,folder in [(9920,'dynamic-05/node2'),(9921,'dynamic-05/node4')]:
 queue=b/folder;state=json.loads((queue/'queue-state.json').read_text());out=b/'r256-composition-453/upper-candidates'/str(tag)/'route';row=dict(tag=tag,active=state['active'],finished={k:v for k,v in state['finished'].items()if 'sready992'in k})
 for p in [out/'receipt.json',queue/('00-g-sready992-r256-route-'+str(tag)+'.log')]:
  if p.exists():row[str(p)]=p.read_text()[-6000:]
 rows.append(row)
print(json.dumps(rows))
'''
raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]);out=Path(__file__).parent/'control162-read998';out.mkdir(exist_ok=True);(out/(str(time.time_ns())+'.json')).write_bytes(raw);print(raw.decode())

