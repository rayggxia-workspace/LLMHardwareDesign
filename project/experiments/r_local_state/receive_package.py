"""Locally receive every archive member and all six native views without extraction."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, tarfile

p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--server-receipt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
assert not a.out.exists(),'Never overwrite a prior reception receipt'
def digest(stream):
 h=hashlib.sha256();size=0
 while True:
  block=stream.read(1024*1024)
  if not block:break
  size+=len(block);h.update(block)
 return dict(sha256=h.hexdigest(),bytes=size)
server=json.loads(a.server_receipt.read_text());assert server['passed']is True
with a.archive.open('rb')as f:actual=digest(f)
assert actual['sha256']==server['sha256']and actual['bytes']==server['bytes']
rows={};manifest=None;qualification=None;root=None;members=0
with tarfile.open(a.archive,'r|gz')as tar:
 for member in tar:
  members+=1;path=PurePosixPath(member.name)
  assert not path.is_absolute()and'..'not in path.parts
  assert member.isdir()or member.isfile(),'Unexpected link or special archive member'
  if root is None:root=path.parts[0]
  assert path.parts[0]==root
  if member.isdir():continue
  rel=str(PurePosixPath(*path.parts[1:]));assert rel and rel not in rows
  f=tar.extractfile(member)
  if rel in ['MANIFEST.json','QUALIFICATION.json']:
   data=f.read();row=dict(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
   if rel=='MANIFEST.json':manifest=json.loads(data)
   else:qualification=json.loads(data)
  else:row=digest(f)
  assert row['bytes']==member.size;rows[rel]=row
assert manifest is not None and qualification['passed']and qualification['native_leaf_qualified']
assert set(rows)==set(manifest)|{'MANIFEST.json'}
for name,row in manifest.items():assert rows[name]==row,(name,rows[name],row)
for name,row in server['six_files'].items():assert rows['native/'+name]==row
assert {Path(n).suffix for n in server['six_files']}=={'.v','.sdc','.def','.odb','.spef','.gds'}
assert rows['native/layout.png']['bytes']>1000
assert len(rows)==server['members']
result=dict(passed=True,archive=str(a.archive.resolve()),archive_binding=actual,server_receipt_sha256=hashlib.sha256(a.server_receipt.read_bytes()).hexdigest(),capacity=qualification['capacity'],files_received=len(rows),all_member_hashes_verified=True,six_native_files_verified=True,qualification=qualification,manifest_sha256=rows['MANIFEST.json']['sha256'],scope='Actual local archive/member/SHA reception of already qualified exact standalone macro; no merge or system qualification.')
a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='qualification'}))
