"""Verify archive receipt, every member and original committed source bindings."""
import argparse,hashlib,json,re,subprocess,zipfile
from pathlib import Path,PurePosixPath

def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',required=True,type=Path);p.add_argument('--expected-sha256',required=True);p.add_argument('--code-root',required=True,type=Path);p.add_argument('--extract',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 if a.extract.exists()or a.out.exists():raise ValueError('refuse overwrite')
 if not re.fullmatch('[0-9a-f]{64}',a.expected_sha256)or sha(a.archive.read_bytes())!=a.expected_sha256:raise ValueError('outer archive SHA')
 with zipfile.ZipFile(a.archive)as z:
  names=z.namelist()
  if len(names)!=len(set(names))or len(names)>50000:raise ValueError('duplicate/excessive members')
  if sum(i.file_size for i in z.infolist())>2*(1<<30):raise ValueError('unexpected unpacked size')
  for i in z.infolist():
   path=PurePosixPath(i.filename)
   if path.is_absolute()or'..'in path.parts or'\\'in i.filename or':'in i.filename or (i.external_attr>>16)&0o170000==0o120000:raise ValueError('unsafe archive path')
  index=json.loads(z.read('artifact-index.json'))['files']
  if set(index)|{'artifact-index.json'}!=set(names):raise ValueError('index member inventory')
  for name,row in index.items():
   raw=z.read(name)
   if len(raw)!=row['bytes']or sha(raw)!=row['sha256']:raise ValueError('member SHA/size '+name)
  checked=0;commits=set()
  for phase in ['phase5','phase8','phase9','phase13','phase14']:
   binding=json.loads(z.read(phase+'/binding.json'));commit=binding['commit']
   if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('source commit')
   commits.add(commit)
   for name,expected in binding['sources'].items():
    member=phase+'/'+name;raw=z.read(member)
    if sha(raw)!=expected:raise ValueError('binding source SHA')
    if name.startswith('down_scale/')or name.startswith('integer_precision/'):repo='project/experiments/'+name
    else:repo='project/experiments/server_models/'+name
    actual=subprocess.check_output(['git','-c','credential.interactive=never','-c','credential.username=Liangruizhi','show',commit+':'+repo],cwd=a.code_root)
    if raw!=actual:raise ValueError('does not match original committed source '+member)
    checked+=1
  a.extract.mkdir()
  for info in z.infolist():
   dest=(a.extract/info.filename).resolve()
   if not dest.is_relative_to(a.extract.resolve()):raise ValueError('extract escapes root')
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(info.filename))
 result={'status':'PASS','archive_sha256':a.expected_sha256,'archive_bytes':a.archive.stat().st_size,'indexed_members':len(index),'git_source_files_checked':checked,'original_source_commits':sorted(commits),'scope':'received exact artifact bytes/source bindings; model and arithmetic acceptance require their own receipts/replay'}
 a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
