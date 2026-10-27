"""Read only this issue's explicit run and save an immutable local evidence index."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

REMOTE = r'''
import hashlib,json,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121')
assert root.parent==base and root.name.startswith('block-v1-')
manifest=json.loads((root/'manifest.json').read_text())
state=json.loads((root/'dispatch-state.json').read_text())
assert manifest['run_id']==state['run_id']==root.name
result=dict(remote_root=str(root),manifest=manifest,manifest_sha256=hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest(),state=state,tasks={})
if (root/'source.tar').exists():
 result['source_archive_sha256']=hashlib.sha256((root/'source.tar').read_bytes()).hexdigest()
 assert result['source_archive_sha256']==manifest['source_archive_sha256']
ids=[x['job_id'] for x in state['tasks'].values() if x.get('job_id')]
assert all(x.isdigit()for x in ids)
result['sacct']=subprocess.check_output(['sacct','-n','-P','-j',','.join(ids),'--format=JobIDRaw,State,ExitCode,Elapsed,TotalCPU,MaxRSS,AllocCPUS,NodeList'],universal_newlines=True) if ids else ''
for task in manifest['tasks']:
 p=root/'tasks'/task['id']
 data={'job_id':state['tasks'].get(task['id'],{}).get('job_id'),'artifacts':{}}
 for relative in ['joint-node-binding.json','joint-routed.json','joint-rc-native.json','measured-joint-rc.json','native-node-queue.json','queue-live.json','native-c8-edit-full-drc.json','native-composed-physical-control.json','native-composed-controls-group.json','native-c8-qualification-group.json','native-projection-control.json','native-projection-control-group.json','native-c8-tie-lec.json','native-c8-tie-lec-group.json','native-tie-formal-control.json','native-tie-formal-control-group.json','native-c8-graph-inputs.json','native-c8-graph-inputs-group.json','native-qa-occupancy.json','native-qa-occupancy-group.json','supply-model-correction.json','native-c8-formal-diagnosis.json','native-c8-formal-diagnosis-group.json','native-c8-probe.json','native-c8-probe-group.json','routing-preflight.json','native-c8-location.json','native-c8-location-group.json','native-whole-drc.json','native-whole-drc-group.json','native-escape-finish.json','native-escape-finish-group.json','native-escape-probe.json','native-escape-group.json','upper-mask-readback.json','rewrite-plan.json','native-glue.json','native-composed-initialization.json','native-composed-function.json','native-composed-group.json','native-view-group.json','native-timing-model-probe.json','native-timing-model-probe-group.json']:
  file=p/relative
  if file.is_file():
   raw=file.read_bytes()
   data['artifacts'][relative]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),content=json.loads(raw.decode()))
 for relative in ['native-via-qualification-group.json','native-via-route-group.json','native-pin-access-probe.json','passive-endpoint-audit.json','native-diagnosis-group.json','native-passive-endpoint-probe.json','native-allocation-group.json','used-signal-drivers.tsv','native-boundary-diagnostic.json','native-boundary-physical.json','native-constant-control.json','physical-functional-proof.json'] + ['receipt.json','test.json','database.json','capabilities.json','build.json','inventory.json','fsv-qualified.json','fv-runtime.json','fv-case.json','direct-field-view.json','primitive-geometry.json','odb-geometry.json','extraction-tool-info.json','native-rule-check.json','probe/route-check.json','negative/receipt.json','physical-inputs.json','native-gds-layers.json','native-config-index.json','native-preparation.json','native-floorplan-input.json','native-boundary-audit.json','native-candidate.json','native-sta-control.json','native-physical-control.json','native-formal-control.json','native-physical-receiver.json','native-drc-summary.json','native-view-generation.json','partial-field-patch.json','partial-field-fv.json','partial-geometry-group.json','field-window.json','routed-field.json','shared109-structural-proof.json','transaction6k-structural-proof.json','geometry-check.json','klayout/mapping.json','reference-patterns/manifest.json','reference-pilot.json','reference-shard.json','reference-fit.json','heldout-inputs.json','heldout-rc.json','mixed0/received/receipt.json','mixed1/received/receipt.json','graph-field-patch.json','graph-build-controls.json','graph-field-fv.json','graph-geometry-group.json','routed-graph-field.json','routed-graph-view.json','capture-field-patch.json','capture-build-controls.json','capture-field-fv.json','capture-geometry-group.json','native-final-function.json','native-drc-location.json','native-cell-gate-probe.json','cell-gate-geometry.json','native-antenna-fixture.json','native-diode-hook.json']:
  file=p/relative
  if file.is_file():
   if relative=='reference-patterns/manifest.json' and file.stat().st_size>256*1024:
    # Summary fields precede the very large cases array in the writer's
    # schema. Hash the complete immutable file with bounded login-node RAM.
    digest=hashlib.sha256();prefix=b'';marker=b'  "cases": ['
    with file.open('rb')as stream:
     for chunk in iter(lambda:stream.read(1024*1024),b''):
      digest.update(chunk)
      if marker not in prefix:
       prefix+=chunk
       assert len(prefix)<=2*1024*1024,'summary prefix missing'
    assert marker in prefix
    content=json.loads(prefix.split(marker,1)[0].rstrip().rstrip(b',')+b'\n}')
    content['large_case_array_and_trailing_fields_omitted_from_index']=True
    data['artifacts'][relative]=dict(bytes=file.stat().st_size,sha256=digest.hexdigest(),content=content)
    continue
   raw=file.read_bytes()
   try:
    content=json.loads(raw.decode())
    if relative=='native-boundary-diagnostic.json':
     differences=content['top_port_differences']
     content['top_port_difference_count']=len(differences)
     content['top_port_differences']=[row for row in differences if tuple(row['port']) in [('adebug',6),('mdebug',4)]]
     content['index_projection']='Only the two currently unmatched top-port records are embedded; all original port snapshots, differences and complete diagnostic remain unchanged on server and are bound by receipt plus outer report SHA256/bytes. Counts and strict rejection remain unchanged.'
    if relative=='native-physical-receiver.json':
     timing=content.get('timing',{})
     if 'explicit_unused_internal_outputs'in timing:
      omitted=timing.pop('explicit_unused_internal_outputs')
      timing['explicit_unused_internal_output_count']=len(omitted)
      content['index_projection']='Unused-output name table omitted only; original complete unchanged server report is bound by outer SHA256/bytes. All gates/counts/extremes remain.'
    if relative=='receipt.json' and len(content.get('outputs',{}))>1000:
     outputs=content['outputs']
     content['outputs']={name:digest for name,digest in outputs.items()
                        if not name.startswith('reference-patterns/') or name=='reference-patterns/manifest.json'}
     content['individual_scene_hashes_omitted_from_index']=len(outputs)-len(content['outputs'])
     content['full_receipt_binding']='Original server receipt retained; outer bytes/SHA bind the complete unchanged file'
    if len(raw)>256*1024 and relative=='reference-patterns/manifest.json':
     content={key:value for key,value in content.items() if key!='cases'}
     content['large_case_array_omitted_from_index']=True
   except (ValueError,UnicodeError): content={'unparsed_tail':raw.decode(errors='replace')[-3000:]}
   data['artifacts'][relative]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),content=content)
 if (p/'job.log').exists():
  raw=(p/'job.log').read_bytes()
  data['job_log']=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),tail=raw.decode(errors='replace')[-3000:])
 result['tasks'][task['id']]=data
print(json.dumps(result))
'''


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('run_id')
    p.add_argument('out',type=Path)
    a=p.parse_args()
    assert re.fullmatch(r'block-v1-[0-9]{8}-[0-9]{3}',a.run_id)
    root='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/'+a.run_id
    command='python3 -c '+shlex.quote(REMOTE)+' '+shlex.quote(root)
    data=subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12','yuzelu@10.129.166.172',command])
    result=json.loads(data)
    result['collected_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'index.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'run_id':a.run_id,'saved':str(a.out/'index.json'),'sacct':result['sacct'],
                      'passed_receipts':{name:item['artifacts'].get('receipt.json',{}).get('content',{}).get('passed')for name,item in result['tasks'].items()}},indent=2))
