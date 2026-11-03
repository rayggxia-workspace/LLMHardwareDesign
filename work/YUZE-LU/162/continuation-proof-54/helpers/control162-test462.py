import subprocess,shlex
q="""from pathlib import Path
import subprocess,json,time,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-padding-bank-unit-slurm-462';assert not out.exists();job='95204';queue=b/'dynamic-04/node25';state=json.loads((queue/'queue-state.json').read_text());assert len(state['active'])<=5
details=subprocess.check_output(['scontrol','show','job',job,'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node25 'in details
forecast=0
for name in state['active']:forecast+=json.loads((queue/'pending'/(name+'.json')).read_text())['forecast_gib']
mem=json.loads(subprocess.check_output(['srun','--jobid='+job,'--overlap','-n1','-c1','python3','-c',"import json;print(json.dumps({k:int(v.split()[0])*1024 for k,v in(line.split(':',1)for line in open('/proc/meminfo'))}))"],universal_newlines=True));required=((forecast+1)*1.2+16)*1024**3;assert required<mem['MemAvailable']
source=b/'source-451';manifest=json.loads((source/'source-manifest.json').read_text());inputs={}
for name in ['test_reset_link_banks.py','reset_link_banks.py']:
 p=source/'project/experiments/control_v1'/name;digest=hashlib.sha256(p.read_bytes()).hexdigest();assert digest==manifest['files'][str(p.relative_to(source))];inputs[str(p)]=digest
cmd=['srun','--jobid='+job,'--exclusive','-n1','-c16','python3','-m','unittest','discover','-s',str(source/'project/experiments/control_v1'),'-p','test_reset_link_banks.py'];out.mkdir();start=time.time();p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True);(out/'stdout.log').write_text(p.stdout);(out/'stderr.log').write_text(p.stderr);assert p.returncode==0 and 'Ran 3 tests'in p.stderr and 'OK'in p.stderr
receipt=dict(passed=True,started_at=start,completed_at=time.time(),job=job,job_details=details,source_commit=manifest['commit'],inputs=inputs,command=cmd,returncode=p.returncode,tests=3,active_forecast_gib=forecast,test_forecast_gib=1,required_bytes=required,actual_mem_available_bytes=mem['MemAvailable'],active_before=state['active'],whole_system_qualified=False,scope='Actual three bank validator tests in own existing node25 allocation; original5active16CPU slots plus one16CPU test slot, no new parent or CPU overcommit. Four exact padding-load corruption cases rejected plus original bank/state checks. No physical/function/system qualification.');receipt['outputs']={n:hashlib.sha256((out/n).read_bytes()).hexdigest()for n in ['stdout.log','stderr.log']};(out/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(dict(passed=True,tests=3,required_bytes=required,available_bytes=mem['MemAvailable'])))
"""
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
