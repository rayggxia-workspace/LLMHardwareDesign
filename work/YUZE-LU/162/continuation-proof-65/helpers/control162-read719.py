import subprocess,shlex
code=r'''from pathlib import Path
import json,time,hashlib,subprocess
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');q=b/'dynamic-07/node7';rows=[]
state=json.loads((q/'queue-state.json').read_text())
for name in state['active']:
 p=q/'pending'/(name+'.json');s=json.loads(p.read_text());a=s['args'];rows.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),spec=s))
out=b/'r256-node7-live-readback-719';assert not out.exists();out.mkdir();(out/'specs.json').write_text(json.dumps(rows,indent=2))
mem=subprocess.check_output(['srun','--jobid=96297','--overlap','-n1','-c1','python3','-c',"import json;print(json.dumps({k:int(v.split()[0]) for k,v in [l.split(':',1) for l in open('/proc/meminfo')] if k=='MemAvailable'}))"],universal_newlines=True)
(out/'mem.json').write_text(mem)
print(json.dumps(dict(rows=[dict(path=r['path'],sha256=r['sha256'],forecast_gib=r['spec']['forecast_gib'],source=r['spec']['source_root'],script=r['spec']['script'],args=r['spec']['args'])for r in rows],mem=json.loads(mem))))
'''
compile(code,'remote719','exec');print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],universal_newlines=True))
