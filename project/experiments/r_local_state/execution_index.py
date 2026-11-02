"""Snapshot own frozen sources and observed receipts; running outputs are not qualification."""
from pathlib import Path
import argparse,json,hashlib,tarfile,datetime,subprocess
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--jobs',type=Path,required=True);a=p.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[];archives={};jobs=json.loads(a.jobs.read_text())['attempt_to_job'];needed_source_sets=set();skipped_archives=[]
for index in sorted(a.root.glob('attempt[0-9][0-9][0-9]/FILES.sha256')):
 needed_source_sets.add(frozenset(line.split(None,1)[1].lstrip('*')for line in index.read_text().splitlines()if line.strip()))
for f in sorted(a.root.glob('source*.tar')):
 with tarfile.open(f)as t:
  entries=[m for m in t.getmembers()if m.isfile()]
  if frozenset(m.name for m in entries)not in needed_source_sets:
   skipped_archives.append({'name':f.name,'reason':'No actual frozen source index has this member scope; unrelated contents not hashed'});continue
  commit=t.pax_headers.get('comment');manifest={m.name:hashlib.sha256(t.extractfile(m).read()).hexdigest()for m in entries}
 archives[f.name]={'sha256':sha(f),'bytes':f.stat().st_size,'git_archive_commit':commit,'source_members':manifest}
for d in sorted(a.root.glob('attempt[0-9][0-9][0-9]')):
 row={'attempt':d.name,'job':jobs.get(d.name),'source_files':{n:sha(d/n)for n in ['FILES.sha256','run.sbatch','source-check.log']if(d/n).is_file()},'receipts':{},'supersession':{}}
 if(d/'FILES.sha256').is_file():
  actual={line.split(None,1)[1].lstrip('*'):line.split(None,1)[0]for line in(d/'FILES.sha256').read_text().splitlines()if line.strip()}
  row['exact_source_archive_matches']=[name for name,v in archives.items()if v['source_members']==actual]
  row['source_archive_binding_verified']=bool(row['exact_source_archive_matches'])
 for name in ['physical/receipt.json','evaluation/receipt.json','netlist-queue/receipt.json','preroute-lec/receipt.json','controls/receipt.json','native-complete/receipt.json','benchmark/receipt.json','path-diagnosis/receipt.json','STAGE_RECEIPT.json']:
  f=d/name
  if f.is_file():row['receipts'][name]={'sha256':sha(f),'content':json.loads(f.read_text())}
 for f in list(d.glob('SUPERSEDED.json'))+list(d.glob('REPLACED*.json')):
  row['supersession'][f.name]={'sha256':sha(f),'content':json.loads(f.read_text())}
 rows.append(row)
ids=','.join(map(str,sorted(set(jobs.values()))))
sacct=subprocess.check_output(['sacct','-n','-X','-j',ids,'-P','--format=JobIDRaw,JobName%48,State,ExitCode,Elapsed,AllocCPUS,NodeList'],universal_newlines=True)
result={'snapshot_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'root':str(a.root),'archives':archives,'skipped_unused_archive_scopes':skipped_archives,'attempts':rows,'sacct':sacct,'scope':'Snapshot of this issue only; hashes of actual frozen source archives are immutable. Unused broader archive contents are not examined. Still-running stage outputs are not accepted final evidence. No macro qualification inferred.'}
Path('EXECUTION_INDEX_SNAPSHOT.json').write_text(json.dumps(result,indent=2)+'\n')
