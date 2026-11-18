"""Replace only this task's obsolete E32 validators, preserving their logs."""
import json
from pathlib import Path
import subprocess
import sys

bundle=Path(sys.argv[1]);root=bundle.parent;head=sys.argv[2]
rows=[]
for name in ('closure-v5-deploy-6fbd77f9','closure-v5-qwen-de9fd4be'):
    for row in json.loads((root/name/'jobs.json').read_text()):
        if name=='closure-v5-deploy-6fbd77f9' and row['model']=='qwen3':continue
        if name=='closure-v5-qwen-de9fd4be':row['model']='qwen3'
        row.setdefault('directory',str(root/name))
        rows.append(row)
observers={(r['model'],r['phase']):r for r in rows if r['variant']=='observe'}
retries=[r for r in rows if r['variant']=='e32-18']
assert len(retries)==14 and len(observers)==14
old=[str(r['job']) for r in retries]
subprocess.run(['scancel',*old],check=False)
receipts=json.loads((bundle/'jobs.json').read_text()) if (bundle/'jobs.json').exists() else []
for oldrow in retries:
    model,phase=oldrow['model'],oldrow['phase']
    if any(r['model']==model and r['phase']==phase for r in receipts):continue
    source=oldrow['command'][-3]
    observer=observers[(model,phase)];accepted=Path(observer['directory'])/('deployment-%s-observe-%s'%(observer['job'],phase))
    complete=(accepted/'results.sha256').exists() and json.loads((accepted/'result/acceptance.json').read_text()).get('passed') is True
    command=['sbatch','--parsable','--time=0','--job-name=mdt-280e32-'+model+'-'+phase[:3]]
    if not complete:command+=['--dependency=afterok:'+str(observer['job'])]
    command+=['run_deployment.sbatch',source,'e32-18',phase]
    job=subprocess.check_output(command,cwd=bundle,universal_newlines=True).strip()
    assert job.isdigit()
    receipts.append(dict(job=job,model=model,phase=phase,variant='e32-18',command=command,directory=str(bundle),
        source_commit=head,replaces_job=str(oldrow['job']),reason='allow only weight_wait_ps timing changes; all numerical/traffic checks retained',
        cpus=12,partition='v6_384',time_limit='UNLIMITED'))
    (bundle/'jobs.json').write_text(json.dumps(receipts,indent=2)+'\n')
    print('SUBMITTED',model,phase,job,flush=True)
subprocess.run(['squeue','-j',','.join(x['job'] for x in receipts),'-o','%.18i %.30j %.10T %.12l %.18R'],check=True)
