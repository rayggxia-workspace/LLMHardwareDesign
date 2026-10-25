"""Portable stdlib byte receiver: no extraction and no assumptions from file names."""
import argparse,hashlib,json,tarfile
from pathlib import Path,PurePosixPath
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
def sha(f):
 h=hashlib.sha256()
 with f.open('rb')as s:
  for b in iter(lambda:s.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def need(v,s):
 if not v:raise ValueError(s)
m=json.loads((a.bundle/'archive.json').read_text());need(m['status']=='ARCHIVE_CREATED_RECEPTION_PENDING','archive identity');need(sha(a.bundle/'index.json')==m['index_sha256'],'index SHA');need(sha(a.bundle/'artifacts.tar.gz')==m['archive_sha256'] and(a.bundle/'artifacts.tar.gz').stat().st_size==m['archive_bytes'],'archive SHA/size');idx=json.loads((a.bundle/'index.json').read_text());need(idx['schema']=='physical98-whole-task-artifact-index-v1','index schema');expected={q['path']:q for q in idx['included']};need(len(expected)==len(idx['included'])==m['files'],'unique complete inventory');seen={};total=0
with tarfile.open(a.bundle/'artifacts.tar.gz','r|gz')as t:
 for q in t:
  name=q.name;path=PurePosixPath(name);need(not path.is_absolute()and '..'not in path.parts and name in expected and name not in seen,'safe unique indexed member');e=expected[name]
  if q.islnk():
   need(q.linkname in seen,'hard link to previously verified member');size,h=seen[q.linkname]
  else:
   need(q.isfile(),'only regular payload or declared prior hard link');s=t.extractfile(q);hsh=hashlib.sha256();size=0
   while True:
    b=s.read(8*1024*1024)
    if not b:break
    size+=len(b);hsh.update(b)
   h=hsh.hexdigest()
  need(size==e['bytes']and h==e['sha256'],'member bytes/SHA '+name);seen[name]=(size,h);total+=size
need(set(seen)==set(expected) and total==idx['total_file_bytes']==m['total_file_bytes'],'all indexed members received')
receipt={'status':'PASS_INDEPENDENT_ALL_ARCHIVED_MEMBER_BYTES_AND_SHA_NOT_EXPERIMENT_ACCEPTANCE','archive_sha256':m['archive_sha256'],'index_sha256':m['index_sha256'],'members':len(seen),'total_file_bytes':total,'limits':['Byte integrity is not functional, timing, electrical or manufacturing acceptance. Refer to exact experiment receivers.','No extraction or execution of archive members.']};need(not a.out.exists(),'unique receiver output');a.out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
