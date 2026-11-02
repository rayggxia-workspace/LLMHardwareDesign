"""Read this AF16 task's own job states and persisted log/receipt tails."""
from pathlib import Path
import json,subprocess
task=Path('/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/af16-cd8dfc9-20261102')
def run(argv):
 r=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=15)
 return {'argv':argv,'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
rows=[]
for p in sorted(task.glob('deploy-r*.json')):
 d=json.loads(p.read_text());job=d.get('job_id');attempt=p.stem.replace('deploy-','')
 if not job:continue
 row={'run':attempt,'job':job,'queue':run(['squeue','-h','-j',job,'-o','%i %j %T %C %M %R']),
 'accounting':run(['sacct','-n','-j',job,'-o','JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,NodeList'])}
 q=task/'runs'/attempt/'results/run-receipt.json'
 if q.is_file():
  v=json.loads(q.read_text());row['receipt']={k:v.get(k) for k in ['status','failure','node','source_commit','started_utc','ended_utc','output_check']}
  row['commands']=[{'label':x['label'],'exit_code':x['exit_code']} for x in v['commands']]
 for name in ['build-af16.log','simulate-af16.log']:
  q=task/'runs'/attempt/'logs'/name
  if q.is_file():row[name]=q.read_text(errors='replace')[-2800:]
 for ext in ['out','err']:
  q=task/'slurm'/('zenanyan-af16-'+job+'.'+ext)
  if q.is_file():row['slurm_'+ext]=q.read_text(errors='replace')[-1800:]
 rows.append(row)
print(json.dumps(rows,indent=2))
