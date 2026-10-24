"""Archive only this authorized Issue68 server tree after explicit acceptance receipts.
No weights or other users' paths are traversed. Existing outputs are never replaced.
"""
import argparse, hashlib, json, os, sys, zipfile
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()

def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--binding',type=Path,required=True);p.add_argument('--require',action='append',required=True)
 a=p.parse_args();root=a.root.resolve();out=a.out.resolve()
 if str(root)!='/public/home/yuzelu/RuizhiLiang/issue68-range-service-20261024':raise ValueError('authorized exact root required')
 if out.parent!=root or out.exists()or not out.name.startswith('delivery'):raise ValueError('new direct delivery directory required')
 binding=json.loads(a.binding.read_text());assert binding['archive_results_sha256']==sha(__file__)and binding['commit']
 receipts=[]
 for rel in a.require:
  path=(root/rel).resolve()
  if not path.is_relative_to(root)or path.is_symlink():raise ValueError('receipt path')
  val=json.loads(path.read_text());status=val.get('status','')
  if not status.startswith('PASS'):raise ValueError((rel,status))
  receipts.append({'path':rel,'sha256':sha(path),'status':status})
 files=[]
 for current,dirs,names in os.walk(root,followlinks=False):
  dirs[:]=sorted(d for d in dirs if not (root/Path(current).relative_to(root)/d).is_symlink()and d!='tmp'and not (Path(current)==root and d.startswith('delivery')))
  for name in sorted(names):
   if Path(current)==root and name.endswith('-'+os.environ.get('SLURM_JOB_ID','NO_CURRENT_JOB')+'.log'):continue
   path=Path(current)/name
   if path.is_symlink()or not path.is_file():raise ValueError('non regular artifact')
   files.append(path)
 out.mkdir();entries={};dest=out/'full-results01.zip'
 with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True)as z:
  for path in files:
   before=path.stat();key=path.relative_to(root).as_posix();digest=sha(path)
   z.write(path,key);after=path.stat()
   if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise RuntimeError('artifact changed while archiving: '+key)
   entries[key]={'bytes':before.st_size,'sha256':digest}
  z.writestr('ARCHIVE_INDEX.json',json.dumps({'source':binding,'root':str(root),'files':entries,'required_receipts':receipts},sort_keys=True,indent=2)+'\n')
 with zipfile.ZipFile(dest)as z:
  if z.testzip()is not None:raise ValueError('archive CRC failed')
  names=z.namelist()
  if len(names)!=len(set(names))or set(names)!=set(entries)|{'ARCHIVE_INDEX.json'}:raise ValueError('archive member set')
  if json.loads(z.read('ARCHIVE_INDEX.json'))['files']!=entries:raise ValueError('archive index mismatch')
  for name,expected in entries.items():
   h=hashlib.sha256();size=0
   with z.open(name)as f:
    for b in iter(lambda:f.read(8<<20),b''):h.update(b);size+=len(b)
   if size!=expected['bytes']or h.hexdigest()!=expected['sha256']:raise ValueError('archived member SHA mismatch: '+name)
 result={'status':'PASS_ARCHIVED_WITH_MEMBER_SHA_AND_CRC','source':binding,'archive':{'path':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest)},'files':len(entries),'uncompressed_bytes':sum(x['bytes']for x in entries.values()),'required_receipts':receipts,'old_input':'Issue66 original data remain read-only external dependency; index previous full-results01.zip separately','limitations':'Stored files, receipt hashes, archive member SHA/bytes and CRC; does not re-execute arithmetic, source legitimacy, RTL or quality. Archive job own final log is excluded and external.'}
 save(out/'delivery.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
