"""Own-server evidence archive preserving failed attempts and original Git byte proof."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from contracts import CONTRACT
from inputs import sha,put
ROOT=Path(__file__).resolve().parents[3]

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert a.root.resolve()==Path('/public/home/yuzelu/RuizhiLiang/issue104-gdn-state-20261025')and a.out.parent==a.root;a.out.mkdir(exist_ok=False);bd=json.loads((ROOT/'binding.json').read_text())
 for n,h in bd['sources'].items():assert sha(ROOT/n)==h
 proof=json.loads((a.root/'local-audit/git-original-source.json').read_text());source_checks=0
 for phase,x in proof['phases'].items():
  assert sha(a.root/phase/'source.zip')==x['source_zip_sha256']
  for n,e in x['files'].items():q=a.root/phase/n;assert q.stat().st_size==e['bytes']and sha(q)==e['sha256'];source_checks+=1
 assert json.loads((a.root/'cost01/cost.json').read_text())['status']=='PASS_COMPLETE_GDN_L2_LOGIC_ONLY_NOT_SYSTEM_SIGNOFF'
 assert json.loads((a.root/'negative01/receipt.json').read_text())['status']=='PASS_FULL_RECEIVER_REJECTS_REHASHED_SEMANTIC_MUTATIONS'
 files=[]
 for f in sorted(a.root.rglob('*')):
  rel=f.relative_to(a.root)
  if rel.parts[0]in('tmp',a.out.name)or rel.parts[0].startswith(('delivery','byte-receive')):continue
  if f.is_symlink():raise ValueError('symlink '+str(rel))
  if not f.is_file():continue
  if'obj'in rel.parts and f.name not in('Vgdn104','Vwide_test104'):continue
  if len(rel.parts)==1 and f.name.startswith(('archive','verify-archive'))and f.suffix=='.log':continue
  files.append((f,rel.as_posix()))
 def select(n):
  q=Path(n);top=q.parts[0]
  if top=='local-audit':return True
  if top==ROOT.name and q.name!='source.zip':return True
  if top.startswith('strict-'):return q.name=='receipt.json'
  if top in('input-native3201','input-portable1201'):return q.suffix=='.json'
  if top=='cost01':return q.suffix=='.json'
  if top in('wide01','control01','negative01'):return q.name=='receipt.json'
  if top in('native32-s0-01','native32-s1-01','portable12-s0-01','portable12-s1-01','protocol-s0-01','protocol-s1-01','map01','gateprepare01','gatebuild01','gate-first-s0-01','gate-first-s1-01','gate-rescale-s0-01','gate-rescale-s1-01','rtl-first-s0-01','rtl-first-s1-01','rtl-rescale-s0-01','rtl-rescale-s1-01'):return q.suffix in('.json','.jsonl')and'obj'not in q.parts
  return False
 full=[];selected=[]
 with zipfile.ZipFile(a.out/'full.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=4)as z,zipfile.ZipFile(a.out/'selected.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as s:
  for f,n in files:
   data=f.read_bytes();e={'path':n,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()};z.writestr(n,data);full.append(e)
   if select(n):s.writestr(n,data);selected.append(e)
  for archive,entries,kind in((z,full,'full'),(s,selected,'selected')):archive.writestr('MANIFEST.json',json.dumps({'schema':'gdn104-byte-archive-v1','kind':kind,'source':bd,'contract':CONTRACT,'original_git_source_file_checks':source_checks,'files':entries},indent=2,sort_keys=True)+'\n')
 ix={'schema':'gdn104-delivery-index-v1','status':'ARCHIVED_AWAITING_INDEPENDENT_BYTES','source':bd,'root':str(a.root),'contract':CONTRACT,'original_git_source_file_checks':source_checks,'failure_retention':'build01 reserved Verilog keyword failure preserved; no output overwritten','full':{'path':str(a.out/'full.zip'),'bytes':(a.out/'full.zip').stat().st_size,'sha256':sha(a.out/'full.zip'),'entries':len(full)},'selected':{'path':str(a.out/'selected.zip'),'bytes':(a.out/'selected.zip').stat().st_size,'sha256':sha(a.out/'selected.zip'),'entries':len(selected)}};put(a.out/'index.json',ix);print(json.dumps(ix))
if __name__=='__main__':main()
