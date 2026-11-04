import subprocess,shlex,json
q="""from pathlib import Path
import json,hashlib,time,subprocess
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');q=b/'dynamic-08/node6';out=b/'r256-native-batch-admission-904';assert not out.exists();out.mkdir();rows=[]
for name in json.loads((q/'queue-state.json').read_text())['active']:
 p=q/'pending'/(name+'.json');raw=p.read_bytes();s=json.loads(raw);a=s['args'];rows.append(dict(name=name,path=str(p),sha256=hashlib.sha256(raw).hexdigest(),source=s['source_root'],forecast_gib=s['forecast_gib'],out=a[a.index('--out')+1],spec=s));(out/(name+'.json')).write_bytes(raw)
mem=json.loads(subprocess.check_output(['srun','--jobid=97097','--overlap','-n1','-c1','python3','-c',"import json;print(json.dumps({k:int(v.split()[0]) for k,v in [l.split(':',1)for l in open('/proc/meminfo')]if k=='MemAvailable'}))"],universal_newlines=True))
r=dict(time=time.time(),rows=rows,mem=mem,whole_system_qualified=False);(out/'receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(dict(rows=[{k:v for k,v in r.items()if k!='spec'}for r in rows],mem=mem)))
"""
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
