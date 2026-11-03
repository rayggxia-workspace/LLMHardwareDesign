"""Export only this task's finalized A16 text evidence; never build binaries."""
from pathlib import Path
import hashlib,json,subprocess,tarfile
task=Path('/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a16-f665230-20261102')
out=task/'exports/c02';assert not out.exists();out.mkdir(parents=True)
paths=[];attempts=[];last_manifest=None
for p in sorted(task.glob('deploy-r*.json')):
 d=json.loads(p.read_text());job=d['job_id'];attempt=p.stem.replace('deploy-','')
 receipt=json.loads((task/'runs'/attempt/'results/run-receipt.json').read_text());assert receipt['status'] in ['PASS','FAIL']
 attempts.append({'run':attempt,'job':job,'status':receipt['status'],'source':receipt['source_commit']})
 for rel in ['deploy-'+attempt+'.json','submit-'+attempt+'.sbatch','input-'+attempt+'/source-manifest.json','runs/'+attempt+'/results/run-receipt.json','slurm/zenanyan-a16-'+job+'.out','slurm/zenanyan-a16-'+job+'.err']:
  assert (task/rel).is_file(),rel;paths.append(rel)
 paths.extend(q.relative_to(task).as_posix() for q in sorted((task/'runs'/attempt/'logs').glob('*.log')))
 r=subprocess.run(['sacct','-n','-j',job,'-o','JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,NodeList'],stdout=subprocess.PIPE,stderr=subprocess.PIPE);assert r.returncode==0
 q=out/('accounting-'+job+'.txt');q.write_bytes(r.stdout);paths.append(q.relative_to(task).as_posix())
 last_manifest=json.loads((task/('input-'+attempt)/'source-manifest.json').read_text())
 for x in last_manifest['files']:
  raw=(task/('input-'+attempt)/x['path']).read_bytes();assert len(raw)==x['bytes'] and hashlib.sha256(raw).hexdigest()==x['sha256'],x['path']
assert attempts and attempts[-1]['status']=='PASS'
rows=[]
for rel in paths:
 raw=(task/rel).read_bytes();rows.append({'path':rel,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
metadata={'schema_version':1,'scope':'A16 text evidence only; builds retained server-side','server_task_root':str(task),'attempts':attempts,'source_inputs_last_reverified':len(last_manifest['files']),'files':rows}
m=out/'evidence-manifest.json';m.write_text(json.dumps(metadata,indent=2)+'\n')
archive=out/'text-evidence.tar.gz'
with tarfile.open(str(archive),'w:gz') as t:
 for rel in paths:t.add(str(task/rel),arcname=rel,recursive=False)
 t.add(str(m),arcname='evidence-manifest.json',recursive=False)
raw=archive.read_bytes();print(json.dumps({'archive':str(archive),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'files':len(rows),'attempts':attempts},indent=2))
