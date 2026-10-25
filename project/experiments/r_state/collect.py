"""Own-server evidence archive, preserving failed attempts and original Git bytes."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from contracts import CONTRACT
ROOT=Path(__file__).resolve().parents[3]
sha=lambda b:hashlib.sha256(b).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',newline='\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert a.root.resolve()==Path('/public/home/yuzelu/RuizhiLiang/issue99-r-state-20261025');assert a.out.parent==a.root;a.out.mkdir(exist_ok=False);bd=json.loads((ROOT/'binding.json').read_text())
 for n,h in bd['sources'].items():assert sha((ROOT/n).read_bytes())==h
 proof=json.loads((a.root/'local-audit/git-original-source.json').read_text());source_checks=0
 for phase,x in proof['phases'].items():
  assert sha((a.root/phase/'source.zip').read_bytes())==x['source_zip_sha256']
  for n,e in x['files'].items():
   b=(a.root/phase/n).read_bytes();assert len(b)==e['bytes']and sha(b)==e['sha256'],phase+'/'+n;source_checks+=1
 for mode in ['real','protocol','boundary']:
  for st in [0,1]:
   x=json.loads((a.root/f'receipt-{mode}{st}05.json').read_text());assert x['contract']==CONTRACT and x['status']==('PASS_FULL_HEAD_RTL_BOUNDARIES'if mode=='boundary'else'PASS_FULL_HEAD_RTL_BIGINT')
 assert json.loads((a.root/'negative02/receipt.json').read_text())['status']=='PASS_REHASHED_ACTUAL_FILES_REJECTED'
 assert json.loads((a.root/'gate-receive01/manifest.json').read_text())['status']=='PASS_RAW_MAPPED_GATE_TWO_REAL_CHECKPOINTS'
 assert json.loads((a.root/'gate-schema01.json').read_text())['status']=='PASS_STRICT_GATE_ROWS_AND_EQUAL_CYCLES'
 assert json.loads((a.root/'cost02.json').read_text())['status']=='PASS_COMPLETE_HEAD_L2_LOGIC_ONLY_NOT_SYSTEM_SIGNOFF'
 files=[]
 for pth in sorted(a.root.rglob('*')):
  rel=pth.relative_to(a.root)
  if rel.parts[0]in ['tmp',a.out.name]or rel.parts[0].startswith(('delivery','byte-receive')):continue
  if pth.is_symlink():raise ValueError('unexpected symlink '+str(rel))
  if not pth.is_file():continue
  if 'obj'in rel.parts and pth.name!='Vr99':continue
  if len(rel.parts)==1 and pth.name.startswith(('archive','verify-archive'))and pth.suffix=='.log':continue
  files.append((pth,rel.as_posix()))
 entries=[];selected=[]
 def choose(name):
  p=Path(name);top=p.parts[0]
  if top.startswith('phase')and top in ['phase7',ROOT.name]and p.name!='source.zip':return True
  if top=='local-audit':return True
  if len(p.parts)==1 and(p.name.startswith('receipt-')and p.name.endswith('05.json')or p.name in ['cost02.json','gate-schema01.json','gate-pilot-decision.json']):return True
  if top in ['real005','real105','protocol005','protocol105','boundary005','boundary105','map04','gateprep01','cpbuild-rtl01','cpbuild-gate01','gate-first0-pilot01','gate-first101','gate-rescale001','gate-rescale101','rtl-first001','rtl-first101','rtl-rescale001','rtl-rescale101','gate-pilot-receive01','gate-receive01','inputs06']:
   return p.suffix in ['.json','.jsonl']and 'obj'not in p.parts
  if top=='negative02':return p.name.endswith('receipt.json')or p.suffix=='.log'
  return False
 with zipfile.ZipFile(a.out/'full.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=4)as z,zipfile.ZipFile(a.out/'selected.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as q:
  for path,name in files:
   data=path.read_bytes();e={'path':name,'bytes':len(data),'sha256':sha(data)};z.writestr(name,data);entries.append(e)
   if choose(name):q.writestr(name,data);selected.append(e)
  for out,arr,kind in[(z,entries,'full'),(q,selected,'selected')]:out.writestr('MANIFEST.json',json.dumps({'schema':'r99-byte-archive-v1','kind':kind,'source':bd,'contract':CONTRACT,'original_git_source_file_checks':source_checks,'files':arr},sort_keys=True,indent=2)+'\n')
 ix={'schema':'r99-delivery-index-v1','status':'ARCHIVED_AWAITING_INDEPENDENT_BYTES','source':bd,'root':str(a.root),'contract':CONTRACT,'full':{'path':str(a.out/'full.zip'),'bytes':(a.out/'full.zip').stat().st_size,'sha256':sha((a.out/'full.zip').read_bytes()),'entries':len(entries)},'selected':{'path':str(a.out/'selected.zip'),'bytes':(a.out/'selected.zip').stat().st_size,'sha256':sha((a.out/'selected.zip').read_bytes()),'entries':len(selected)},'original_git_source_file_checks':source_checks,'failure_retention':'inputs01/03 metadata mismatch, build01/map01 syntax failure, dependency cancellation records, all prior pass/raw outputs retained; no overwritten output'};put(a.out/'index.json',ix);print(json.dumps(ix))
if __name__=='__main__':main()
