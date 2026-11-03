"""Export only F16 task text evidence; builds/binaries remain on server."""
from pathlib import Path
import hashlib,json,subprocess,tarfile
task=Path('/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/f16-febc042-20261102')
destination=task/'exports/c01';assert not destination.exists();destination.mkdir(parents=True)
paths=[]
for run,job in [('r01','95206'),('r02','95209')]:
 for rel in ['deploy-'+run+'.json','submit-'+run+'.sbatch','input-'+run+'/source-manifest.json',
             'runs/'+run+'/results/run-receipt.json','slurm/zenanyan-f16-'+job+'.out','slurm/zenanyan-f16-'+job+'.err']:
  assert (task/rel).is_file(),rel;paths.append(rel)
 for p in sorted((task/'runs'/run/'logs').glob('*.log')):paths.append(p.relative_to(task).as_posix())
 r=subprocess.run(['sacct','-n','-j',job,'-o','JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,NodeList'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 assert r.returncode==0
 p=destination/('accounting-'+job+'.txt');p.write_bytes(r.stdout);paths.append(p.relative_to(task).as_posix())
manifest=json.loads((task/'input-r02/source-manifest.json').read_text())
for x in manifest['files']:
 raw=(task/'input-r02'/x['path']).read_bytes();assert len(raw)==x['bytes'] and hashlib.sha256(raw).hexdigest()==x['sha256'],x['path']
rows=[]
for rel in paths:
 raw=(task/rel).read_bytes();rows.append({'path':rel,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
metadata={'schema_version':1,'scope':'F16 text evidence only; obj/build binaries excluded and retained on server','server_task_root':str(task),'source_inputs_r02_reverified':len(manifest['files']),'files':rows}
m=destination/'evidence-manifest.json';m.write_text(json.dumps(metadata,indent=2)+'\n')
archive=destination/'text-evidence.tar.gz'
with tarfile.open(str(archive),'w:gz') as t:
 for rel in paths:t.add(str(task/rel),arcname=rel,recursive=False)
 t.add(str(m),arcname='evidence-manifest.json',recursive=False)
raw=archive.read_bytes();print(json.dumps({'archive':str(archive),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'files':len(rows)},indent=2))
