"""Archive own immutable Issue88 evidence and explicit previous-input dependencies."""
import argparse,hashlib,json,zipfile
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--receipt',default='receive-all02');a=p.parse_args();root=a.root.resolve();out=a.out.resolve()
 if str(root)!='/public/home/yuzelu/RuizhiLiang/issue88-electrical-repair-20261025'or out.parent!=root:raise ValueError('own root only')
 if out.exists():raise ValueError('new delivery only')
 receipt=json.loads((root/a.receipt/'receipt.json').read_text())
 if receipt['status']!='PASS_REPAIRED_GRAPH_GATE_MATH_AND_DECLARED_TIMING_RECEPTION'or{v['variant']for v in receipt['variants']}!={0,1,2,3}:raise ValueError('complete independent reception required')
 files=[]
 for q in sorted(root.rglob('*')):
  if q.is_symlink():raise ValueError('no symlinks')
  if not q.is_file():continue
  rel=q.relative_to(root)
  if rel.parts[0]=='tmp'or('obj'in rel.parts and q.name!='Vchain84')or rel.parts[0].startswith('delivery'):continue
  files.append(q)
 out.mkdir();records=[{'path':q.relative_to(root).as_posix(),'bytes':q.stat().st_size,'sha256':sha(q)}for q in files]
 excluded={'mapped.json','cut.json','baseline.json','tied.json','mapped.v','cut.v','cells.v','tied.v','repaired.v','repaired.odb','source.zip','Vchain84','dispatch.zip'}
 selected=[x['path']for x in records if Path(x['path']).name not in excluded and x['bytes']<=5<<20 and not Path(x['path']).name.startswith(('negative-net-','negative-dff-','independent-v'))]
 # Retain independent parse scripts/logs/command receipts, excluding only large parsed netlists.
 selected+= [x['path']for x in records if Path(x['path']).name.startswith('independent-v')and not x['path'].endswith('.json')or(Path(x['path']).name.startswith('independent-v')and x['path'].endswith('-command.json'))]
 selected=sorted(set(selected));archives=[]
 for name,names in [('full-results.zip',[r['path']for r in records]),('selected.zip',selected)]:
  path=out/name
  with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
   for n in names:z.write(root/n,n)
  archives.append({'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path),'members':len(names)})
 binding=json.loads((Path(__file__).resolve().parents[3]/'binding.json').read_text())
 index={'schema':'issue88-server-delivery-v1','source_commit':binding['commit'],'receipt':a.receipt+'/receipt.json','receipt_sha256':sha(root/a.receipt/'receipt.json'),'files':records,'selected_paths':selected,'archives':archives,'dependencies':{'issue84_root':'/public/home/yuzelu/RuizhiLiang/issue84-cache-share-20261025','issue86_root':'/public/home/yuzelu/RuizhiLiang/issue86-gate-sta-20261025','input_manifest_sha256':receipt['input_manifest_sha256'],'original_logic':'Exact four original Issue86 prepare-v{0..3}01 declared memory cuts. Independent original parse results and all original manifest SHAs retained. Physical packed vectors remain original Issue84 input01, read-only, indexed by SHA.'},'limits':['Eight selected complete final gate runs plus full original-pin graph certificate; store82 remains behavioral in replay and excluded in STA.','No placement, wire parasitics, real source impedance, clock tree, target SRAM/ROM or target process timing qualification.','All prior pilot/export/receiver scheduling failures retained, not silently replaced.','Full archive excludes compiler intermediate objects; exact gate binaries retained.']}
 (out/'index.json').write_text(json.dumps(index,indent=2)+'\n');print(json.dumps(archives))
if __name__=='__main__':main()