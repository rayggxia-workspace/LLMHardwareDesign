"""Collect bounded closed-task evidence; never copy native databases or SPEFs."""
import argparse
import base64
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

HOST='yuzelu@10.129.166.172'
BASE='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121'


def collect(run_id,destination):
    assert re.fullmatch(r'block-v1-\d{8}-\d{3}',run_id)
    assert not destination.exists(),'Use a new snapshot destination'
    remote=r'''
import base64,hashlib,json,pathlib,datetime
r=pathlib.Path(BASE)/RUN
files={};excluded=[]
def add(path,expected=None):
 data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
 if expected is not None:assert expected==digest,(str(path),'receipt hash mismatch')
 name=str(path.relative_to(r))
 if len(data)>2*1024*1024:
  excluded.append(dict(path=name,sha256=digest,bytes=len(data),reason='bounded evidence size limit'))
  if path.name=='interconnect-result.json':
   d=json.loads(data);zeros=d.pop('zero_fanout_unannotated_drivers')
   assert not any(zeros.values())
   d['zero_fanout_unannotated_driver_summary']=dict(count=len(zeros),connected_count=0,
    canonical_json_sha256=hashlib.sha256(json.dumps(zeros,sort_keys=True,separators=(',',':')).encode()).hexdigest())
   compact=json.dumps(d,indent=2).encode();assert len(compact)<2*1024*1024
   files[name.replace('.json','-summary.json')]=dict(sha256=hashlib.sha256(compact).hexdigest(),bytes=len(compact),base64=base64.b64encode(compact).decode(),receipt_bound=False,
    derived_from=dict(path=name,sha256=digest,original_receipt_bound=expected is not None,transformation='Only replace verified all-zero fanout dictionary with count and canonical dictionary SHA256; all other fields retained'))
  return
 files[name]=dict(sha256=digest,bytes=len(data),base64=base64.b64encode(data).decode(),receipt_bound=expected is not None)
for name in ['manifest.json','node-queue.json','dispatch-state.json','node-queue-state.json','rejected-batch.json']:
 p=r/name
 if p.exists():add(p)
allowed={'interconnect-probe.json','interconnect-prepare.json','interconnect-result.json',
 'sta.log','summary.tsv','links.tsv','annotation.rpt','annotation-connectivity.tsv',
 'timing.rpt','electrical.rpt','check-setup.rpt','constraints-readback.sdc','sta.tcl','wrapper.v'}
for receipt in sorted(r.glob('tasks/*/receipt.json')):
 add(receipt);d=json.loads(receipt.read_text())
 for name,digest in d['outputs'].items():
  if pathlib.PurePosixPath(name).name in allowed:add(receipt.parent/name,digest)
 # job.log is deliberately excluded from original worker output hashes.
 log=receipt.parent/'job.log'
 if log.exists():add(log)
q=r/'tasks/native-node-queue'
if (q/'exit-code.txt').exists():
 for name in ['allocation.txt','started.txt','finished.txt','exit-code.txt','job.sh','job.log']:
  p=q/name
  if p.exists():add(p)
print(json.dumps(dict(run_id=RUN,remote_directory=str(r),captured_utc=datetime.datetime.utcnow().isoformat()+'Z',files=files,excluded=excluded)))
'''.replace('BASE',repr(BASE)).replace('RUN',repr(run_id))
    result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',HOST,'python3 -'],
                          input=remote,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert result.returncode==0,result.stderr
    payload=json.loads(result.stdout);destination.mkdir(parents=True)
    records={}
    for name,row in payload.pop('files').items():
        p=destination/name
        assert destination.resolve() in p.resolve().parents
        data=base64.b64decode(row.pop('base64'))
        assert hashlib.sha256(data).hexdigest()==row['sha256'] and len(data)==row['bytes']
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);records[name]=row
    index=dict(**payload,local_verified_utc=datetime.now(timezone.utc).isoformat(),files=records,
               scope='Only closed receipts and bounded evidence. Native SPEF/Verilog/ODB stay on authorized server. Queue snapshots may be in progress; no qualification inferred.')
    (destination/'index.json').write_text(json.dumps(index,indent=2)+'\n')
    rows=[]
    for path in sorted(destination.glob('tasks/*/interconnect-result*.json')):
        r=json.loads(path.read_text())
        paths=r['link_paths'];worst=min(paths,key=lambda k:paths[k]['max']['slack_ns'])
        forward=[p['max']['slack_ns']for k,p in paths.items()if k.startswith('f')]
        rows.append(dict(task=path.parent.name,pair=r['pair'],topology=r['topology'],
                         length_um=r['length_um'],variant=r['variant'],counts=r['counts'],
                         min_setup_ns=r['min_link_setup_ns'],min_hold_ns=r['min_link_hold_ns'],
                         min_forward_setup_ns=min(forward),ready_setup_ns=paths['r000']['max']['slack_ns'],
                         worst_link=worst,worst_path=paths[worst]['max'],
                         declared_model_passed=r['declared_model_passed'],
                         native_graph_preserved=r['native_preservation']['passed']))
    (destination/'measurements.json').write_text(json.dumps(dict(run_id=run_id,rows=rows),indent=2)+'\n')
    print(json.dumps(dict(run_id=run_id,files=len(records),bytes=sum(x['bytes']for x in records.values()),
                          measurements=len(rows),declared_model_passes=sum(r['declared_model_passed']for r in rows))))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('run_id');p.add_argument('destination',type=Path)
    a=p.parse_args();collect(a.run_id,a.destination)
