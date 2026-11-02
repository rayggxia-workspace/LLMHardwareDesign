"""Snapshot own frozen sources and observed receipts; running outputs are not qualification."""
from pathlib import Path
import argparse,json,hashlib,tarfile,datetime,subprocess
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--jobs',type=Path,required=True);a=p.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[];archives={};jobs=json.loads(a.jobs.read_text())['attempt_to_job']
for f in sorted(a.root.glob('source*.tar')):
 with tarfile.open(f)as t:commit=t.pax_headers.get('comment')
 archives[f.name]={'sha256':sha(f),'bytes':f.stat().st_size,'git_archive_commit':commit}
for d in sorted(a.root.glob('attempt[0-9][0-9][0-9]')):
 row={'attempt':d.name,'job':jobs.get(d.name),'source_files':{n:sha(d/n)for n in ['FILES.sha256','run.sbatch','source-check.log']if(d/n).is_file()},'receipts':{},'supersession':{}}
 for name in ['physical/receipt.json','evaluation/receipt.json','netlist-queue/receipt.json','preroute-lec/receipt.json','controls/receipt.json','STAGE_RECEIPT.json']:
  f=d/name
  if f.is_file():row['receipts'][name]={'sha256':sha(f),'content':json.loads(f.read_text())}
 for f in list(d.glob('SUPERSEDED.json'))+list(d.glob('REPLACED*.json')):
  row['supersession'][f.name]={'sha256':sha(f),'content':json.loads(f.read_text())}
 rows.append(row)
ids=','.join(map(str,sorted(set(jobs.values()))))
sacct=subprocess.check_output(['sacct','-n','-X','-j',ids,'-P','--format=JobIDRaw,JobName%48,State,ExitCode,Elapsed,AllocCPUS,NodeList'],universal_newlines=True)
result={'snapshot_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'root':str(a.root),'archives':archives,'attempts':rows,'sacct':sacct,'scope':'Snapshot of this issue only; hashes of source archives are immutable. Still-running stage outputs are not accepted final evidence. No macro qualification inferred.'}
Path('EXECUTION_INDEX_SNAPSHOT.json').write_text(json.dumps(result,indent=2)+'\n')
