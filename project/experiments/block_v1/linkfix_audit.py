"""Read-only exact-source audit for full-bus repair experiments."""
import argparse,json
from pathlib import Path
from interconnect_launch import remote


def capture(root,destination,last):
    spec=json.loads((root/'project/experiments/block_v1/interconnect-sources.json').read_text())
    deliveries=json.loads((root/'project/experiments/block_v1/revision300-deliveries.json').read_text())
    code=r"""
import json,hashlib,subprocess
from pathlib import Path
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121')
spec=__SPEC__;deliveries=__DELIVERIES__
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as stream:
  for b in iter(lambda:stream.read(1048576),b''):h.update(b)
 return h.hexdigest()
native={};runs={};jobs=set()
for kind,row in spec['macros'].items():
 native[kind]={}
 for name,wanted in row['hashes'].items():
  p=Path(row['verilog']).parent/name
  if name=='6_final.gds':
   folder=base/deliveries['gates'][kind]/('revision300-drc-'+kind)
   r=json.loads((folder/'receipt.json').read_text());assert r['passed']
   f=folder/'five-macro-drc.json';assert sha(f)==r['outputs'][f.name]
   d=json.loads(f.read_text());assert d['passed'];p=Path(d['gds']['path'])
  assert sha(p)==wanted
  native[kind][name]=dict(path=str(p),sha256=wanted,bytes=p.stat().st_size)
for number in range(925,__LAST__+1):
 p=base/('block-v1-20261029-%03d'%number);assert p.exists()
 row=dict(source_archive_sha256=sha(p/'source.tar'),files={})
 f=p/'src/bundle-manifest.json'
 if f.exists():
  manifest=json.loads(f.read_text());row.update(source_commit=manifest['source_commit'],source_members=len(manifest['files']),source_manifest_sha256=sha(f))
 else:row['qualification']='Not executed: staged source archive only'
 for name in ['manifest.json','node-queue.json','dispatch-state.json','node-queue-state.json','cohost.json','cohost-launched.json','opportunistic.json','short-step-launched.json','opportunistic-short-step.json','opportunistic-electrical-step.json','source-superseded.json']:
  f=p/name
  if not f.exists():continue
  d=json.loads(f.read_text());row['files'][name]=dict(sha256=sha(f),bytes=f.stat().st_size)
  if name=='dispatch-state.json':jobs.update(str(v['job_id'])for v in d['tasks'].values()if v.get('job_id'))
  if name in ('cohost-launched.json','short-step-launched.json'):
   job=str(d.get('job_id',d.get('parent_job','')))
   assert job.isdigit() and '--jobid='+job in d['argv'] and d['new_allocation'] is False
   jobs.add(job);row['cohost_allocation']=job
 runs[str(number)]=row
live=subprocess.check_output(['squeue','-j',','.join(sorted(jobs)),'-h','-o','%i %T %N'],universal_newlines=True)
assert not live.strip(),'Owned repair experiment allocation still active'
accounting=subprocess.check_output(['sacct','-j',','.join(sorted(jobs)),'-n','-P','-o','JobIDRaw,State,ExitCode,NodeList,Elapsed,MaxRSS'],universal_newlines=True)
print(json.dumps(dict(passed=True,native_baseline_unchanged=native,runs=runs,slurm_accounting=accounting,no_owned_active_allocations=True,
 qualification='Original eighteen production files unchanged; repaired-copy qualifications and complete-route measurements are separate receipt-bound results. An interrupted cohost grants no unfinished task qualification.')))
""".replace('__SPEC__',repr(spec)).replace('__DELIVERIES__',repr(deliveries)).replace('__LAST__',str(last))
    result=json.loads(remote(code));destination.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(native_files=sum(map(len,result['native_baseline_unchanged'].values())),runs=len(result['runs']),no_active=True)))

if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('destination',type=Path);parser.add_argument('--last',type=int,required=True)
    args=parser.parse_args();capture(Path(__file__).resolve().parents[3],args.destination,args.last)
