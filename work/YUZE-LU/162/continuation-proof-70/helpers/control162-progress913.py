import subprocess,shlex,json,time
from pathlib import Path
q="""from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-native-batch-regression-902';rows=[]
for p in sorted(root.iterdir()):
 if p.is_dir():rows.append(dict(name=p.name,outputs=len(list(p.rglob('router-output.txt'))),binaries=len(list(p.rglob('router'))),logs=len(list(p.rglob('router.log')))))
print(json.dumps(dict(time=time.time(),rows=rows,receipts=[str(p)for p in root.glob('*.json')])))
"""
raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]);out=Path(__file__).parent/'control162-progress913';out.mkdir(exist_ok=True);(out/(str(time.time_ns())+'.json')).write_bytes(raw);d=json.loads(raw);print(json.dumps(dict(time=d['time'],groups=len(d['rows']),newer=[r for r in d['rows']if r['name']in ['directional-bidirectional','weighted-bidirectional']],receipts=d['receipts'])))
