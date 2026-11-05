from pathlib import Path
h=Path(__file__).parent
s=(h/'control162-read904.py').read_text();a=s.index('q="""');z=s.index('"""',a+5)
q='''from pathlib import Path
import json,hashlib,time,subprocess
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-native-batch-admission-914';assert not out.exists();out.mkdir();rows=[];nodes=[]
for job,folder,seeds in [(97097,'dynamic-08/node6',[8860]),(95155,'dynamic-03/node5',[8861,8862])]:
 q=b/folder;forecasts=[]
 for name in json.loads((q/'queue-state.json').read_text())['active']:
  p=q/'pending'/(name+'.json');raw=p.read_bytes();s=json.loads(raw);a=s['args'];forecasts.append(dict(name=name,forecast_gib=s['forecast_gib']))
  if '--out'in a and any('/upper-candidates/'+str(seed)+'/'in a[a.index('--out')+1]for seed in seeds):rows.append(dict(name=name,path=str(p),sha256=hashlib.sha256(raw).hexdigest(),source=s['source_root'],spec=s));(out/(name+'.json')).write_bytes(raw)
 mem=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',"import json;print(json.dumps({k:int(v.split()[0]) for k,v in [l.split(':',1)for l in open('/proc/meminfo')]if k=='MemAvailable'}))"],universal_newlines=True));nodes.append(dict(job=job,folder=folder,forecasts=forecasts,mem=mem))
assert len(rows)==3
r=dict(time=time.time(),rows=rows,nodes=nodes,whole_system_qualified=False);(out/'receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(dict(rows=[{k:v for k,v in r.items()if k!='spec'}for r in rows],nodes=nodes)))
'''
code='import subprocess,shlex\nq='+repr(q)+"\nprint(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())\n";compile(code,'read914','exec');(h/'control162-read914.py').write_bytes(code.encode())
s=(h/'control162-refill905-remote.py').read_text().replace('sready905-native-batch-refill-node6','sready915-native-batch-refill').replace('sready902-native-batch-controls','sready902-native-batch-fullchains').replace("assert len(tasks['tasks'])==1","assert len(tasks['tasks'])==28").replace("for row in tasks['tasks']:assert Path(row['path']).is_file()","for row in tasks['tasks']:assert sha(row['path'])==row['sha256']")
s=s.replace('r256-native-zero-regression-885','r256-native-batch-regression-902').replace('audit-887','audit-907').replace('admission-904','admission-914')
s=s.replace("[(6, 97097, 'dynamic-08/node6', 8591, 'source-633', 0)]","[(6,97097,'dynamic-08/node6',8860,'source-884',0),(5,95155,'dynamic-03/node5',8861,'source-884',0),(5,95155,'dynamic-03/node5',8862,'source-884',0)]")
needle=" queue=b/folder;state="
replacement=" mem=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',\"import json;print(json.dumps({k:int(v.split()[0]) for k,v in [l.split(':',1)for l in open('/proc/meminfo')]if k=='MemAvailable'}))\"],universal_newlines=True));assert mem['MemAvailable']/1048576>284.8;(record/('fresh-memory-'+str(seed)+'.json')).write_text(json.dumps(dict(time=time.time(),mem=mem,required_available_gib=284.8,passed=True)))\n queue=b/folder;state="
assert s.count(needle)==1;s=s.replace(needle,replacement)
a=s.index("reason='Replace only exact own8591");z=s.index("')\n",a);s=s[:a]+"reason='Replace only exact own8860/8861/8862 all-pin native maze candidates with current453/S5380/S1350/R256 source901 controlled four full seven-stage chains9060-9063. Require actual90271case45negative and907all63legacy byte replays plus911all28spec binding, fresh914rawSHA/UID/job/node/PID/cmd/frozen-source/out/current453graph and per-node MemAvailable284.8GiB for224GiB forecasts. Preserve all old raw/spec/source/failure/partial, best6360 and8301, other own8parents/externalR/foreign. No native, full route, geometry/PG/3RC300MHz or final acceptance inferred.'"+s[z+1:]
s=s.replace("record.mkdir();mem=", "assert json.loads((b/'r256-final-chain-binding-audit-911/receipt.json').read_text())['passed'];record.mkdir();mem=");compile(s,'refill915','exec');(h/'control162-refill915-remote.py').write_bytes(s.encode());print('prepared read914 and strict refill915')
