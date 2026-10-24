"""Archive completed Issue64 evidence; selected data never mean full benchmark."""
import argparse,hashlib,json,zipfile
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def archive(dest,root,names):
 if dest.exists():raise ValueError('refuse archive overwrite')
 index={}
 with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for n in sorted(set(names)):
   p=root/n
   if p.is_symlink()or not p.resolve().is_relative_to(root.resolve())or p.suffix=='.safetensors':raise ValueError('unsafe artifact')
   index[n]={'bytes':p.stat().st_size,'sha256':sha(p)};z.write(p,n)
  z.writestr('artifact-index.json',json.dumps({'files':index},indent=2)+'\n')
 return {'path':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest),'members':len(index)+1}
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--commit',required=True);a=p.parse_args();r=a.root
 dirs=['output01','output02','attention01','attention02','service01','service02','receive01']
 for name in dirs:
  m=json.loads((r/name/('audit.json'if name=='receive01'else'manifest.json')).read_text())
  if m['status']!='PASS':raise ValueError('stage not accepted '+name)
  for f,row in m.get('artifacts',m.get('files',{})).items():
   if sha(r/name/f)!=row['sha256']:raise ValueError('artifact changed')
 allfiles=[];selected=[]
 for d in dirs:
  for f in (r/d).rglob('*'):
   if f.is_file():
    n=f.relative_to(r).as_posix();allfiles.append(n)
    if d.startswith('attention')and f.suffix=='.npz':continue
    selected.append(n)
 for d in ['phase1','phase2','phase3','phase4','llama']:
  for f in (r/d).rglob('*'):
   if f.is_file()and f.name!='source.zip':
    n=f.relative_to(r).as_posix();allfiles.append(n)
    if d!='llama':selected.append(n)
 for f in r.glob('*.log'):allfiles.append(f.name);selected.append(f.name)
 result={'status':'PASS','collection_commit':a.commit,'full':archive(r/'full-results01.zip',r,allfiles),'selected':archive(r/'selected-evidence01.zip',r,selected),'scope':'two output rounds, full attention arithmetic results on server; selected archive keeps2 actual attention cases only; all service graphs/metrics and source snapshots included; no complete model weights; no full-model/PPA acceptance'}
 (r/'delivery01.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
