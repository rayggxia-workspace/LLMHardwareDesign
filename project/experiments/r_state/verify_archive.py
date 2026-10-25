"""Byte-only independent archive receiver; safe on PC (never loads numerical tensors)."""
import argparse,hashlib,json,zipfile
from pathlib import Path
sha=lambda b:hashlib.sha256(b).hexdigest()
def need(v,s):
 if not v:raise ValueError(s)
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--index',type=Path,required=True);p.add_argument('--kind',choices=['full','selected'],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();ix=json.loads(a.index.read_text());data=a.archive.read_bytes();need(len(data)==ix[a.kind]['bytes']and sha(data)==ix[a.kind]['sha256'],'archive index bytes');checks=0;artifact_checks=0
 with zipfile.ZipFile(a.archive)as z:
  names=z.namelist();need(len(names)==len(set(names))and z.testzip()is None,'zip integrity');m=json.loads(z.read('MANIFEST.json'));need(m['schema']=='r99-byte-archive-v1'and m['kind']==a.kind and m['source']==ix['source']and m['contract']==ix['contract'],'archive binding');expected={'MANIFEST.json'}
  for e in m['files']:
   n=e['path'];need(not n.startswith('/')and'..'not in Path(n).parts,'relative archive path');b=z.read(n);need(len(b)==e['bytes']and sha(b)==e['sha256'],'actual archive file '+n);checks+=1;expected.add(n)
  need(set(names)==expected,'no unmanifested bytes');proof=json.loads(z.read('local-audit/git-original-source.json'));gitchecks=0
  for phase,g in proof['phases'].items():
   if phase+'/source.zip'in names:need(sha(z.read(phase+'/source.zip'))==g['source_zip_sha256'],'original source zip')
   for n,e in g['files'].items():
    key=phase+'/'+n
    if key in names:b=z.read(key);need(len(b)==e['bytes']and sha(b)==e['sha256'],'original Git '+key);gitchecks+=1
  if a.kind=='full':
   need(gitchecks==ix['original_git_source_file_checks'],'every original Git source')
   for n in names:
    if n.endswith('/manifest.json'):
     mm=json.loads(z.read(n));parent=n.rsplit('/',1)[0]
     for e in mm.get('artifacts',[]):
      key=parent+'/'+e['path'];b=z.read(key);need(len(b)==e['bytes']and sha(b)==e['sha256'],'nested artifact '+key);artifact_checks+=1
     if mm.get('binary_sha256'):need(sha(z.read(parent+'/obj/Vr99'))==mm['binary_sha256'],'exact compiled executable')
 result={'schema':'r99-byte-receipt-v1','status':'PASS_ARCHIVE_AND_ORIGINAL_GIT_BYTES','kind':a.kind,'archive_sha256':sha(data),'archive_bytes':len(data),'checked_files':checks,'original_git_source_files':gitchecks,'nested_artifact_checks':artifact_checks,'index_sha256':sha(a.index.read_bytes()),'receiver_source_sha256':sha(Path(__file__).read_bytes())};a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
