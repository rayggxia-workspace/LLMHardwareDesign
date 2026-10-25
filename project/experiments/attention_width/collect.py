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
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert a.root==Path('/public/home/yuzelu/RuizhiLiang/issue110-attention-width-20261025')and a.out.parent==a.root;a.out.mkdir(exist_ok=False)
 bd=json.loads((ROOT/'binding.json').read_text())
 for n,h in bd['sources'].items():assert digest(ROOT/n)==h
 assert json.loads((a.root/'analysis01/summary.json').read_text())['status']=='PASS110_PROVED_EQUIVALENT_SAME_CYCLE_RESOURCE_SELECTED_RAW_GATE'
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
  if 'obj'in rel.parts and f.name not in ['Vshared106','Vchain102']:continue
  if len(rel.parts)==1 and f.name.startswith(('archive','verify-archive'))and f.suffix=='.log':continue
  files.append((f,rel.as_posix()))
 selected=[];entries=[]
 def choose(n):
  p=Path(n);top=p.parts[0]
  if top=='local-audit':return True
  if top.startswith('phase'):return p.name=='binding.json'or(top==ROOT.name and p.name!='source.zip')
  if len(p.parts)==1:return p.suffix=='.json'
  if top.startswith(('receive-','gate-receive','proof-receive','numeric-negative','negative','inventory-negative','analysis')):return len(p.parts)==2 and p.name in ['receipt.json','summary.json','gate-receipt.json']
  return p.suffix=='.json'and len(p.parts)==2 and p.name not in ['generic.json','mapped.json','stat.json','extraction.json','math-cones.json','cases.json']and '-proc.json'not in p.name and '-inv.json'not in p.name
 with zipfile.ZipFile(a.out/'full-results.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=4)as z,zipfile.ZipFile(a.out/'selected.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as q:
  for f,n in files:
   e={'path':n,'bytes':f.stat().st_size,'sha256':digest(f)};entries.append(e);z.write(f,n)
   if choose(n):selected.append(n);q.write(f,n)
 index={'schema':'attention110-delivery/1','status':'ARCHIVED_AWAITING_INDEPENDENT_BYTE_RECEPTION','source_commit':bd['commit'],'source':bd,'root':str(a.root),'original_git_source_checks':source_count,'files':entries,'selected_paths':selected,'archives':[{'path':str(a.out/n),'bytes':(a.out/n).stat().st_size,'sha256':digest(a.out/n),'members':len(selected)if n=='selected.zip'else len(entries)}for n in ['full-results.zip','selected.zip']],'exclusions':['Rebuildable obj intermediate C++/object/archive files omitted; actual executed binaries retained.','Current archive jobs logs not sealed while still running; final Slurm/execution receipt delivered separately.'],'limits':['Byte archives do not replace separate mathematical/RTL/gate acceptance.','All frozen sources, actual file-mutant negatives, unrestricted-domain counterexample and failed gate scheduling attempts are retained.']}
 (a.out/'delivery-index.json').write_text(json.dumps(index,indent=2)+'\n',newline='\n');print(json.dumps(index['archives']))
if __name__=='__main__':main()
