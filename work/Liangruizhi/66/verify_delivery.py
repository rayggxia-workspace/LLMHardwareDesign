"""Safely receive the Issue66 selected archive; numerical replay remains separate."""
import argparse,hashlib,json,re,subprocess,zipfile
from pathlib import Path,PurePosixPath

def sha(raw):return hashlib.sha256(raw).hexdigest()

def main():
 p=argparse.ArgumentParser()
 for k in ('archive','repo','extract','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--sha256',required=True);a=p.parse_args()
 if a.extract.exists()or a.out.exists():raise ValueError('new output required')
 if sha(a.archive.read_bytes())!=a.sha256:raise ValueError('outer SHA')
 with zipfile.ZipFile(a.archive)as z:
  names=z.namelist()
  if len(set(names))!=len(names):raise ValueError('duplicate members')
  if sum(i.file_size for i in z.infolist())>128<<20:raise ValueError('selected size limit')
  for info in z.infolist():
   q=PurePosixPath(info.filename)
   if q.is_absolute()or'..'in q.parts or':'in info.filename or'\\'in info.filename or(info.external_attr>>16)&0o170000==0o120000:raise ValueError('unsafe member')
  idx=json.loads(z.read('artifact-index.json'))['files']
  if set(idx)|{'artifact-index.json'}!=set(names):raise ValueError('index inventory')
  for n,r in idx.items():
   raw=z.read(n)
   if len(raw)!=r['bytes']or sha(raw)!=r['sha256']:raise ValueError('member SHA '+n)
  checks=[]
  bindings=sorted(n for n in names if re.fullmatch(r'phase\d+[a-z]?/binding.json',n))
  if len(bindings)!=15:raise ValueError('frozen15 phases')
  for name in bindings:
   folder=name.rsplit('/',1)[0];b=json.loads(z.read(name));commit=b['commit']
   if not re.fullmatch('[a-f0-9]{40}',commit):raise ValueError('commit binding')
   with zipfile.ZipFile(__import__('io').BytesIO(z.read(folder+'/source.zip')))as source:
    if source.read('binding.json')!=z.read(name):raise ValueError('capsule binding')
    if set(source.namelist())!=set(b['sources'])|{'binding.json'}:raise ValueError('capsule inventory')
    for path,digest in b['sources'].items():
     q=PurePosixPath(path)
     if q.is_absolute()or'..'in q.parts or not path.startswith(('project/','work/')):raise ValueError('source path')
     raw=z.read(folder+'/'+path);blob=subprocess.check_output(['git','show',commit+':'+path],cwd=a.repo)
     if raw!=blob or sha(raw)!=digest or source.read(path)!=raw:raise ValueError('Git/source capsule '+path)
     checks.append({'phase':folder,'commit':commit,'file':path,'sha256':digest})
  a.extract.mkdir(parents=True)
  for name in names:
   dest=(a.extract/name).resolve()
   if not dest.is_relative_to(a.extract.resolve()):raise ValueError('escape')
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(name))
 result={'status':'PASS','archive_sha256':a.sha256,'archive_bytes':a.archive.stat().st_size,'indexed_members':len(idx),'phases':len(bindings),'Git_sources':checks,'scope':'outer/member SHA, safe extraction and all15 phase source capsules against original Git blobs; no numerical acceptance by this step'}
 a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps({'status':'PASS','indexed_members':len(idx),'phases':len(bindings),'Git_source_files':len(checks)}))
if __name__=='__main__':main()
