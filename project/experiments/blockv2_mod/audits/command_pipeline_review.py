"""Create a source/receipt review snapshot; full binaries stay at their remote paths."""
import argparse, hashlib, json, tarfile
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--assembly',type=Path,required=True)
p.add_argument('--run',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();root=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
proof=json.loads(a.assembly.read_text())
for name,h in proof['source_sha256'].items():
 if sha(Path(name))!=h:raise ValueError('assembly source changed: '+name)
if not a.run.is_dir():raise ValueError('run directory required')
a.output.mkdir(parents=True,exist_ok=False)
sources={}
for directory in ('rtl','compiler','hardware','tlm','tests','algo1','frontend','audits'):
 for f in (root/directory).rglob('*'):
  if f.is_file() and f.suffix in {'.py','.sv','.svh','.in','.v','.vlt','.cpp','.h','.md','.json','.sh','.sbatch','.ini'} and '__pycache__' not in f.parts:
   sources[str(f.relative_to(root))]=f
for name in proof['source_sha256']:
 f=Path(name)
 if not f.is_relative_to(root):sources['dependencies/'+str(f).lstrip('/')]=f
for name in ('README.md','NATIVE_FLOW.md'):
 sources[name]=root/name
sources['evidence/selected-assembly-receipt.json']=a.assembly
for f in a.run.rglob('*.json'):
 if f.stat().st_size<=2_000_000:sources['evidence/run/'+str(f.relative_to(a.run))]=f
index={name:{'sha256':sha(f),'bytes':f.stat().st_size,'remote_source':str(f.resolve())} for name,f in sorted(sources.items())}
out=a.output/'source.tar.gz'
with tarfile.open(out,'w:gz') as tar:
 for name,f in sorted(sources.items()):tar.add(f,arcname=name,recursive=False)
with tarfile.open(out,'r:gz') as tar:
 for name,row in index.items():
  if hashlib.sha256(tar.extractfile(name).read()).hexdigest()!=row['sha256']:raise ValueError('archive readback '+name)
(a.output/'source-index.json').write_text(json.dumps(index,indent=2)+'\n')
(a.output/'receipt.json').write_text(json.dumps({
 'schema':'command-pipeline-review/1','source_archive_sha256':sha(out),
 'source_index_sha256':sha(a.output/'source-index.json'),'files':len(index),
 'assembly_receipt':str(a.assembly.resolve()),'run_directory':str(a.run.resolve()),
 'archive_readback_verified':True,'runtime_images_included':False,
 'downloaded_to_local':False,'published':False,
 'scope':'review snapshot; functional/performance acceptance is defined by the run receipts'
},indent=2)+'\n')
print(json.dumps({'files':len(index),'output':str(a.output)}))
