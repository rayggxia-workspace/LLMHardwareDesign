"""Read only this task's Slurm status and persisted result/log tails."""
from pathlib import Path
import json,subprocess
task=Path('/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/f16-febc042-20261102')
def run(argv):
 r=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=15)
 return {'argv':argv,'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
receipt={'queue':run(['squeue','-h','-j','95206','-o','%i %j %T %C %M %R']),
 'accounting':run(['sacct','-n','-j','95206','-o','JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,NodeList'])}
p=task/'runs/r01/results/run-receipt.json'
if p.is_file():
 d=json.loads(p.read_text());receipt['run']={k:d.get(k) for k in ['status','failure','node','source_commit','started_utc','ended_utc','output_check']}
 receipt['commands']=[{'label':x['label'],'exit_code':x['exit_code']} for x in d['commands']]
for stream in ['out','err']:
 p=task/'slurm'/('zenanyan-f16-95206.'+stream)
 if p.is_file():receipt['slurm_'+stream]=p.read_text(errors='replace')[-2500:]
for name in ['build-f16.log','simulate-f16.log']:
 p=task/'runs/r01/logs'/name
 if p.is_file():receipt[name]=p.read_text(errors='replace')[-3500:]
print(json.dumps(receipt,indent=2))
