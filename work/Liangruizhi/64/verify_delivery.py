"""Safe archive intake and source snapshot checks; numerical replays are separate."""
import argparse,hashlib,json,subprocess,zipfile
from pathlib import Path,PurePosixPath

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--extract',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.extract.exists()or a.out.exists():raise ValueError('new output paths required')
 if sha(a.archive.read_bytes())!=a.sha256:raise ValueError('outer archive SHA')
 with zipfile.ZipFile(a.archive)as z:
  names=z.namelist()
  if len(set(names))!=len(names):raise ValueError('duplicate members')
  for info in z.infolist():
   q=PurePosixPath(info.filename)
   if q.is_absolute()or'..'in q.parts or':'in info.filename or'\\'in info.filename or (info.external_attr>>16)&0o170000==0o120000:raise ValueError('unsafe archive member')
  idx=json.loads(z.read('artifact-index.json'))['files']
  if set(idx)|{'artifact-index.json'}!=set(names):raise ValueError('index inventory')
  for n,r in idx.items():
   raw=z.read(n)
   if len(raw)!=r['bytes']or sha(raw)!=r['sha256']:raise ValueError('member SHA '+n)
  checks=[]
  for phase,files in [('phase1',{'output.py':('output_sha256','project/experiments/block_decisions/output.py')}),('phase2',{'project/experiments/block_decisions/attention.py':('attention_sha256','project/experiments/block_decisions/attention.py'),'project/experiments/server_models/bounds.py':('bounds_sha256','project/experiments/server_models/bounds.py')}),('phase3',{'receive_attention.py':('receiver_sha256','project/experiments/block_decisions/receive_attention.py')}),('phase4',{'project/experiments/block_decisions/service.py':('service_sha256','project/experiments/block_decisions/service.py'),'project/experiments/rq_ports/model.py':('dependency_sha256','project/experiments/rq_ports/model.py')})]:
   b=json.loads(z.read(phase+'/binding.json'));commit=b.get('commit',b.get('source_commit'))
   for n,(field,repo_path)in files.items():
    raw=z.read(phase+'/'+n);blob=subprocess.check_output(['git','show',commit+':'+repo_path],cwd=a.repo)
    if raw!=blob or sha(raw)!=b[field]:raise ValueError('original Git source '+n)
    checks.append({'commit':commit,'file':repo_path,'sha256':sha(raw)})
  a.extract.mkdir(parents=True)
  for n in names:
   dest=(a.extract/n).resolve()
   if not dest.is_relative_to(a.extract.resolve()):raise ValueError('escape')
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(n))
 result={'status':'PASS','archive_sha256':a.sha256,'bytes':a.archive.stat().st_size,'indexed_members':len(idx),'source_files_checked':checks,'scope':'actual selected archive/Git source integrity; full56 numerical replay remains server receipt; numerical/port qualification separate'};a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps({'status':'PASS','members':len(idx),'Git_source_files':len(checks)}))
if __name__=='__main__':main()
