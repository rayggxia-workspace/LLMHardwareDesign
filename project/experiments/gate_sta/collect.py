"""Package own immutable experiment outputs; dependencies remain indexed on server."""
import argparse,hashlib,json,zipfile
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.root.resolve();out=a.out.resolve()
 if not str(root).startswith('/public/home/yuzelu/RuizhiLiang/issue86-gate-sta-')or out.parent!=root:raise ValueError('own root only')
 if out.exists():raise ValueError('new delivery only')
 if json.loads((root/'receive02/receipt.json').read_text())['status']!='PASS_GATE_MATH_AND_DECLARED_TIMING_RECEPTION':raise ValueError('independent receipt required')
 files=[]
 for q in sorted(root.rglob('*')):
  if q.is_symlink():raise ValueError('no symlinks')
  if not q.is_file():continue
  rel=q.relative_to(root)
  if rel.parts[0]=='tmp' or 'obj'in rel.parts and q.name!='Vchain84':continue
  if rel.parts[0].startswith('delivery'):continue
  files.append(q)
 out.mkdir();records=[{'path':q.relative_to(root).as_posix(),'bytes':q.stat().st_size,'sha256':sha(q)}for q in files]
 excluded={'mapped.json','cut.json','mapped.v','cut.v','cells.v','source.zip','Vchain84'}
 selected=[x['path']for x in records if Path(x['path']).name not in excluded and x['bytes']<=5<<20]
 archives=[]
 for name,names in [('full-results.zip',[r['path']for r in records]),('selected.zip',selected)]:
  path=out/name
  with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
   for n in names:z.write(root/n,n)
  archives.append({'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path),'members':len(names)})
 binding=json.loads((Path(__file__).resolve().parents[3]/'binding.json').read_text())
 index={'schema':'issue86-server-delivery-v1','source_commit':binding['commit'],'files':records,'selected_paths':selected,'archives':archives,'dependencies':{'issue84_root':'/public/home/yuzelu/RuizhiLiang/issue84-cache-share-20261025','input_manifest_sha256':json.loads((root/'receive02/receipt.json').read_text())['input_manifest_sha256'],'mapping':'Original map-v{0..3}03 are byte-reused; exact copies in prepare mapped.json. Input physical payload remains original input01, not duplicated here.'},'limits':['Selected archive includes actual gate outputs and timing evidence; no SRAM macro or physical closure.','Full archive excludes compiler intermediate objects; gate binaries included. Exact external input dependencies remain authorized server read-only.']}
 (out/'index.json').write_text(json.dumps(index,indent=2)+'\n');print(json.dumps(archives))
if __name__=='__main__':main()