"""Read-only source/hash/Slurm audit; no EDA tools or task mutations on login."""
import argparse,json
from pathlib import Path
from interconnect_launch import remote


def capture(root,destination):
    spec=json.loads((root/'project/experiments/block_v1/interconnect-sources.json').read_text())
    deliveries=json.loads((root/'project/experiments/block_v1/revision300-deliveries.json').read_text())
    code=r'''
import json,hashlib,subprocess,re
from pathlib import Path
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121')
spec=SPEC
deliveries=DELIVERIES
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as stream:
  for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
 return h.hexdigest()
native={};runs={};jobs=[];diagnostics={}
for kind,row in spec['macros'].items():
 values={}
 for name,wanted in row['hashes'].items():
  p=Path(row['verilog']).parent/name
  if name=='6_final.gds':
   folder=base/deliveries['gates'][kind]/('revision300-drc-'+kind)
   receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed']
   report=folder/'five-macro-drc.json';assert sha(report)==receipt['outputs'][report.name]
   received=json.loads(report.read_text());assert received['passed']
   p=Path(received['gds']['path'])
  actual=sha(p);assert actual==wanted
  values[name]=dict(path=str(p),sha256=actual,bytes=p.stat().st_size)
 native[kind]=values
for n in range(909,925):
 p=base/('block-v1-20261029-%03d'%n)
 dispatch=json.loads((p/'dispatch-state.json').read_text())
 ids=[str(d['job_id'])for d in dispatch['tasks'].values()if d.get('job_id')];jobs+=ids
 bundle=json.loads((p/'src/bundle-manifest.json').read_text())
 runs[str(n)]=dict(source_commit=bundle['source_commit'],source_archive_sha256=sha(p/'source.tar'),
  source_manifest_sha256=sha(p/'src/bundle-manifest.json'),source_members=len(bundle['files']),
  job_ids=ids,manifest_sha256=sha(p/'manifest.json'),queue_sha256=sha(p/'node-queue.json'))
 if n in (918,919,921):
  for pair in ('mt','ts'):
   task=p/'tasks'/('linkclose-route-'+pair)
   if not task.exists():continue
   files={};reports=[]
   for name in ('route.log','route-inputs.json','route.tcl','route.guide'):
    f=task/name
    if f.exists():files[name]=dict(path=str(f),sha256=sha(f),bytes=f.stat().st_size)
   for f in sorted(task.glob('route-drc.rpt*')):
    text=f.read_text();types={}
    for kind in re.findall(r'violation type: (.+)',text):types[kind]=types.get(kind,0)+1
    reports.append(dict(path=str(f),sha256=sha(f),bytes=f.stat().st_size,violations=sum(types.values()),types=types))
   log=task/'route.log';tail=log.read_text(errors='replace').splitlines()[-15:] if log.exists()else[]
   diagnostics[str(n)+'-'+pair]=dict(files=files,drc_reports=reports,tail=tail,
      qualification='NOT ACCEPTED: failed/cancelled diagnostics. No successful geometry/STA qualification inferred.')
accounting=subprocess.check_output(['sacct','-j',','.join(jobs),'-n','-P','-o','JobIDRaw,State,ExitCode,NodeList,Elapsed,MaxRSS'],universal_newlines=True)
live=subprocess.check_output(['squeue','-j',','.join(jobs),'-h','-o','%i %T %R'],universal_newlines=True)
assert not live.strip(),'An owned experiment allocation is still active; do not publish final closure yet'
print(json.dumps(dict(passed=True,native_baseline_unchanged=native,runs=runs,slurm_accounting=accounting,
  no_owned_active_allocations=True,failed_or_cancelled_diagnostics=diagnostics)))
'''.replace('SPEC',repr(spec)).replace('DELIVERIES',repr(deliveries))
    d=json.loads(remote(code));destination.write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps(dict(native_files=sum(len(v)for v in d['native_baseline_unchanged'].values()),
        runs=len(d['runs']),no_active_allocations=d['no_owned_active_allocations'])))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('destination',type=Path);a=p.parse_args()
    capture(Path(__file__).resolve().parents[3],a.destination)
