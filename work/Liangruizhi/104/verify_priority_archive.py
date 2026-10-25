"""Independent byte-only receiver for the isolated format-priority supplement."""
import argparse,hashlib,json,zipfile
from pathlib import Path
sha=lambda x:hashlib.sha256(x).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--index',type=Path,required=True);p.add_argument('--kind',choices=['full','selected'],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();ix=json.loads(a.index.read_text());assert ix['schema']=='gdn104-format-priority-index-v1';data=a.archive.read_bytes();assert len(data)==ix[a.kind]['bytes']and sha(data)==ix[a.kind]['sha256'];checks=0;gitchecks=0;nested=0
 with zipfile.ZipFile(a.archive)as z:
  names=z.namelist();assert len(names)==len(set(names))and z.testzip()is None;m=json.loads(z.read('MANIFEST.json'));assert m['schema']=='gdn104-format-priority-archive-v1'and m['kind']==a.kind and m['source']==ix['source'];expected={'MANIFEST.json'}
  for e in m['files']:
   n=e['path'];assert isinstance(n,str)and not n.startswith('/')and'..'not in Path(n).parts and'\\'not in n and type(e['bytes'])is int;v=z.read(n);assert len(v)==e['bytes']and sha(v)==e['sha256'];checks+=1;expected.add(n)
  assert set(names)==expected and checks==ix[a.kind]['entries'];receipt=json.loads(z.read('receipt.json'));assert receipt['schema']=='gdn104-format-priority-v1'and receipt['status']=='PASS_MIXED_DOMAIN_PRIORITY_FULL_GROUP_UNCHANGED'and sha(z.read('receipt.json'))==ix['receipt_sha256']and receipt['source']==ix['source']and receipt['main_index_sha256']==ix['main_index_sha256']
  proof=json.loads(z.read('original-git-source.json'));assert proof['commit']==ix['source']['commit']
  for n,e in proof['files'].items():
   key='phase9/'+n;v=z.read(key);assert len(v)==e['bytes']and sha(v)==e['sha256']==ix['source']['sources'][n];gitchecks+=1
  if a.kind=='full':
   assert sha(z.read('phase9/source.zip'))==proof['source_zip_sha256']
   for n in names:
    if n.endswith('/manifest.json'):
     mm=json.loads(z.read(n));parent=n.rsplit('/',1)[0]
     for e in mm.get('artifacts',[]):v=z.read(parent+'/'+e['path']);assert len(v)==e['bytes']and sha(v)==e['sha256'];nested+=1
 out={'schema':'gdn104-format-priority-byte-v1','status':'PASS_SUPPLEMENT_BYTES_ORIGINAL_GIT_AND_BINDINGS','kind':a.kind,'archive_sha256':sha(data),'archive_bytes':len(data),'files_checked':checks,'git_source_checks':gitchecks,'nested_artifact_checks':nested,'main_index_sha256':ix['main_index_sha256'],'index_sha256':sha(a.index.read_bytes()),'receiver_sha256':sha(Path(__file__).read_bytes())};a.out.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf8',newline='\n');print(json.dumps(out))
if __name__=='__main__':main()
