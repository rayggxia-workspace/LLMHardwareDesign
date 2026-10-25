"""Collect all task evidence and failures; no overwrite and no numerical re-labeling."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert a.root==Path('/public/home/yuzelu/RuizhiLiang/issue109-shared-gdn-20261025')and a.out.parent==a.root;a.out.mkdir(exist_ok=False)
 bd=json.loads((ROOT/'binding.json').read_text())
 for n,h in bd['sources'].items():assert digest(ROOT/n)==h
 assert json.loads((a.root/'analysis01/summary.json').read_text())['status']=='PASS_FOUR_PROFILE_SHARED_L2_SELECTED_RAW_GATE_NOT_PHYSICAL'
 audit=json.loads((a.root/'local-audit/git-original-source.json').read_text());source_count=0
 for phase,b in audit['phases'].items():
  assert digest(a.root/phase/'source.zip')==b['source_zip_sha256']
  for n,e in b['files'].items():assert (a.root/phase/n).stat().st_size==e['bytes']and digest(a.root/phase/n)==e['sha256'];source_count+=1
 files=[]
 for f in sorted(a.root.rglob('*')):
  rel=f.relative_to(a.root)
  if rel.parts[0]in ['tmp',a.out.name]or rel.parts[0].startswith(('delivery','byte-receive')):continue
  if f.is_symlink():raise ValueError('unexpected symlink')
  if not f.is_file():continue
  if 'obj'in rel.parts and f.name!='Vshared109':continue
  if len(rel.parts)==1 and f.name.startswith(('archive','verify-archive'))and f.suffix=='.log':continue
  files.append((f,rel.as_posix()))
 selected=[];entries=[]
 def choose(n):
  p=Path(n);top=p.parts[0]
  if top=='local-audit':return True
  if top.startswith('phase'):
   return p.name=='binding.json'or(top==ROOT.name and p.name!='source.zip')
  if top=='analysis01'or top.startswith('final-receive-')or top in ['negative01','inventory-negative01']:return p.name in ['receipt.json','summary.json']
  if len(p.parts)==1:return p.name in ['cost01.json','cost02.json']
  if top in ['input01','map01','build01','qual-build02','gateprepare01','gatebuild01','mixed001','mixed101','qual002','qual102','gate002','gate102','rtl-pilot001','rtl-pilot101']:return p.suffix=='.json'and 'obj'not in p.parts and p.name not in ['generic.json','mapped.json','stat.json']
  return False
 with zipfile.ZipFile(a.out/'full-results.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=4)as z,zipfile.ZipFile(a.out/'selected.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as q:
  for f,n in files:
   e={'path':n,'bytes':f.stat().st_size,'sha256':digest(f)};entries.append(e);z.write(f,n)
   if choose(n):selected.append(n);q.write(f,n)
 index={'schema':'shared109-delivery/1','status':'ARCHIVED_AWAITING_INDEPENDENT_BYTE_RECEPTION','source_commit':bd['commit'],'source':bd,'root':str(a.root),'original_git_source_checks':source_count,'files':entries,'selected_paths':selected,'archives':[{'path':str(a.out/n),'bytes':(a.out/n).stat().st_size,'sha256':digest(a.out/n),'members':len(selected)if n=='selected.zip'else len(entries)}for n in ['full-results.zip','selected.zip']],'exclusions':['Rebuildable obj intermediate C++/object/archive files omitted; actual executed binaries retained.','Current archive jobs logs not sealed while still running; final Slurm/execution receipt delivered separately.'],'limits':['Byte archives do not replace separate mathematical/RTL/gate acceptance.','All earlier source snapshots, raw pilot/formal attempts and superseded qualification input-version protocol remain retained.']}
 (a.out/'delivery-index.json').write_text(json.dumps(index,indent=2)+'\n',newline='\n');print(json.dumps(index['archives']))
if __name__=='__main__':main()
