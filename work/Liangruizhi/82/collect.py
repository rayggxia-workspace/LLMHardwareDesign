"""Archive only explicit Issue82 artifacts; never original model weights/caches or other tasks."""
import argparse,hashlib,json,zipfile
from pathlib import Path

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(8<<20),b''):h.update(block)
 return h.hexdigest()

def desc(path,root):
 return {'path':path.relative_to(root).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)}

def main():
 p=argparse.ArgumentParser(__doc__)
 p.add_argument('--root',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();root=a.root.resolve();out=a.out.resolve()
 if root!=Path('/public/home/yuzelu/RuizhiLiang/issue82-norm-circuit-20261025') or out.parent!=root:raise ValueError('explicit authorized task root only')
 if out.exists():raise ValueError('refuse output overwrite')
 config=json.loads(a.config.read_text());files=set()
 for relative in config['directories']:
  folder=(root/relative).resolve()
  if folder.parent!=root or not folder.is_dir():raise ValueError('non-immediate task artifact directory '+relative)
  for f in folder.rglob('*'):
   if f.is_symlink():raise ValueError('symlink excluded '+str(f))
   if f.is_file():files.add(f)
 for relative in config['files']:
  f=(root/relative).resolve()
  if f.parent!=root or not f.is_file():raise ValueError('non-task log '+relative)
  files.add(f)
 if any('models' in str(f.relative_to(root)) or f.suffix=='.safetensors' for f in files):raise ValueError('weight/cache exclusion')
 out.mkdir()
 entries=[desc(f,root) for f in sorted(files)]
 # Exact frozen source archives remain in primary bundle. Select only metadata,
 # receipts and logs; no actual tensor math is required for PC byte reception.
 selected=[f for f in sorted(files) if f.suffix in ('.json','.log','.md') and f.name not in ('mapped.json','netlist.json','generic.json','vectors.json','cases.json') and not any(x.startswith('negative-')for x in f.relative_to(root).parts) and f.stat().st_size<=12<<20]
 archives=[]
 for name,items,compression in (
  ('full-results.zip',sorted(files),zipfile.ZIP_STORED),
  ('selected.zip',selected,zipfile.ZIP_DEFLATED)):
  target=out/name
  with zipfile.ZipFile(target,'x',compression=compression,allowZip64=True) as z:
   for f in items:z.write(f,f.relative_to(root).as_posix())
  archives.append({**desc(target,root),'members':len(items)})
 index={'schema':'issue82-delivery-v1','root':str(root),'config_sha256':sha(a.config),'collector_sha256':sha(__file__),'source_commit':config['source_commit'],'archives':archives,'files':entries,'selected_paths':[f.relative_to(root).as_posix()for f in selected],'external_inputs':config['external_inputs'],'limits':['Primary archive is exact executed output, including recorded failures and semantic negatives; weights and the original Issue74/76 input capsules remain external.','Selected archive contains metadata only, not a replacement for full integer math acceptance.','Full-row norm and real-M complete-consumer functional RTL and logic-only mapping have separately bound receipts; no full accelerator, SRAM/ROM macro, STA/PPA or application-quality acceptance is implied.']}
 (out/'index.json').write_text(json.dumps(index,indent=2)+'\n')
 print(json.dumps({'archives':archives,'files':len(entries),'index_sha256':sha(out/'index.json')}),flush=True)
if __name__=='__main__':main()
