"""Collect only accepted immutable deployment outputs and verify run manifests."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import tarfile

def digest(p):
    h=sha256()
    with p.open('rb') as f:
        for x in iter(lambda:f.read(4<<20),b''):h.update(x)
    return h.hexdigest()

root,out=map(Path,sys.argv[1:3]);records=[]
for name in ('closure-v5-deploy-6fbd77f9','closure-v5-qwen-de9fd4be',*sys.argv[3:]):
    b=root/name
    jobs=json.loads((b/'jobs.json').read_text())
    if isinstance(jobs,dict):jobs=jobs.get('jobs',jobs)
    if not isinstance(jobs,list):raise ValueError('unknown job receipt '+str(b))
    for job in jobs:
        if str(job['job']) in ('38850016','38850017','38850018','38850019'):continue
        job.setdefault('directory',str(b))
        if name=='closure-v5-qwen-de9fd4be':job.setdefault('model','qwen3')
        records.append(job)
records=list({str(x['job']):x for x in records}.values())
report=[]
with tarfile.open(out,'w:gz') as tar:
    for row in records:
        b=Path(row['directory']);job=str(row['job'])
        run=b/('deployment-%s-%s-%s'%(job,row['variant'],row['phase']))
        manifest=run/'results.sha256'
        if not manifest.exists():report.append(dict(**row,status='not_collected_no_completed_manifest'));continue
        for line in manifest.read_text().splitlines():
            h,f=line.split(maxsplit=1)
            if digest(run/f)!=h:raise ValueError('result SHA changed '+str(run/f))
        acceptance=json.loads((run/'result/acceptance.json').read_text())
        if acceptance.get('passed') is not True:raise ValueError('unaccepted replay')
        base='%s-%s-%s'%(row['model'],row['phase'],row['variant'])
        files=['results.sha256','provenance.json']
        files+=['result/'+f+'.json' for f in ('acceptance','result','deployment-observation','component-observation','arithmetic-observation','ddr-window-energy','dma-windows')]
        if (run/'result/timing-changes.json').exists():files.append('result/timing-changes.json')
        for f in files:tar.add(run/f,arcname=base+'/'+f,recursive=False)
        report.append(dict(**row,status='accepted_and_manifest_verified',manifest_sha256=digest(manifest),archive_directory=base))
out.with_suffix('.json').write_text(json.dumps(dict(jobs=report,archive_sha256=digest(out)),indent=2)+'\n')
print('COLLECTED',sum(x['status']=='accepted_and_manifest_verified' for x in report),'OF',len(report),flush=True)
