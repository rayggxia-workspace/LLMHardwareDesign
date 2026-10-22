"""Read compact observations; freeze terminal receipts without changing remote data."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
receipts=sorted((HERE/'results').glob('*-submission.json'))
REMOTE_SCRIPT=r'''
from pathlib import Path
import hashlib,json,subprocess
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-15')
out={}
for p in sorted(base.iterdir()):
 if not (p/'spec.json').exists(): continue
 spec=json.load(open(p/'spec.json'))
 row={'spec':spec,'exit_code':(p/'exit-code.txt').read_text().strip() if (p/'exit-code.txt').exists() else None}
 for name in ['started.txt','finished.txt','allocation.txt','resource-audit.json','experiment.json','input-sha256.json','strict-pg.json','final-pg/strict-pg.json']:
  f=p/name
  if f.exists():
   row[name]=json.load(open(f)) if f.suffix=='.json' else f.read_text()
 files=sorted((p/'flow/logs').rglob('*.log'),key=lambda f:f.stat().st_mtime) if (p/'flow/logs').exists() else []
 if files: row['last_flow_log']={'path':str(files[-1]),'tail':files[-1].read_text(errors='replace').splitlines()[-8:]}
 row['job_log_tail']=(p/'job.log').read_text(errors='replace').splitlines()[-14:]
 row['metrics']={}
 for f in (p/'flow/logs').rglob('*.json') if (p/'flow/logs').exists() else []:
  if f.name in ('6_report.json','5_2_route.json'):
   d=json.load(open(f));row['metrics'][f.name]={k:v for k,v in d.items() if any(s in k for s in ['timing','area','wirelength','vias','antenna','drc','instance','violations','power','clock','net__count'])}
 for f in (p/'flow/reports').rglob('6_finish.rpt') if (p/'flow/reports').exists() else []:
  row['final_report']=f.read_text()
 for f in p.glob('*-resource.json'): row[f.name]=json.load(open(f))
 f=p/'output.sha256'
 if f.exists(): row['output_manifest_sha256']=hashlib.sha256(f.read_bytes()).hexdigest();row['output_manifest_entries']=len(f.read_text().splitlines())
 out[p.name]=row
print(json.dumps(out))
'''
result=subprocess.run(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3','-'],input=REMOTE_SCRIPT,
                      text=True,capture_output=True,check=True)
data=json.loads(result.stdout)
ids={json.loads(p.read_text())['job_id']:p.stem.removesuffix('-submission') for p in receipts}
acct=subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','sacct -n -P -j '+','.join(ids)+' --format=JobIDRaw,State,ExitCode,Elapsed,Timelimit,AllocCPUS,NodeList'],text=True)
for line in acct.splitlines():
 parts=line.split('|')
 if parts[0] in ids and ids[parts[0]] in data: data[ids[parts[0]]]['scheduler']=line
snapshot=dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=data)
(HERE/'results/latest.json').write_text(json.dumps(snapshot,indent=2)+'\n')
for name,row in data.items():
 print(name,row.get('scheduler',row['exit_code']),row.get('last_flow_log',{}).get('path','').split('/')[-1])
 if row.get('scheduler') and row['scheduler'].split('|')[1] not in ('RUNNING','PENDING') and row.get('output_manifest_sha256'):
  path=HERE/'results'/(name+'-terminal.json')
  if not path.exists(): path.write_text(json.dumps(row,indent=2)+'\n')
