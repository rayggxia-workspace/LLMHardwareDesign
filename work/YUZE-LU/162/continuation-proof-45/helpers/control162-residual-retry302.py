import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
import hashlib,re,time
queue=b/'dynamic-07/node7';root=b/'r256-composition-274';record=b/'route-selection-102/sready302-native-residual-retry';assert not record.exists();record.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=root/'native-sta/receipt.json';r=json.loads(receipt.read_text());audit=root/'native-sta/native-system-audit.json';assert r['execution_passed']and r['typed_native_timing_passed']and r['native_coverage_audit_passed']and json.loads(audit.read_text())['passed']and r['outputs'][audit.name]==sha(audit)
rows=[]
for old,new in [('00-e-sready263-native-residual','00-e-sready302-native-residual'),('00-f-sready263-native-pin-load','00-f-sready302-native-pin-load')]:
 p=queue/'pending'/(old+'.json');raw=p.read_text();spec=json.loads(raw.replace(str(root/'native-residual'),str(root/'native-residual302')).replace(str(root/'native-pin-load'),str(root/'native-pin-load302')));dest=Path(spec['args'][spec['args'].index('--out')+1]);target=queue/'pending'/(new+'.json');assert re.fullmatch('[a-z0-9_-]+',new)and not target.exists()and not dest.exists();tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(target);rows.append(dict(path=str(target),sha256=sha(target),spec=spec,original_spec=str(p),original_spec_sha256=sha(p)))
(record/'tasks.json').write_text(json.dumps(dict(tasks=rows,time=time.time(),actual_complete_native_receipt_sha256=sha(receipt),actual_audit_sha256=sha(audit),whole_system_qualified=False,reason='Previous exact residual command raced with STA final receipt publication after audit ready signal. Actual complete diagnostic receipt now exists and binds positive native audit, every retained actual endpoint and all electrical gates passed. Fresh residual302/pin302 retry uses same frozen source258/computation/limits; failed originals retained. No rerun of qualified physical blocks, no new allocation, no gate change.'),indent=2));print('fresh queued',len(rows),'native setup/hold',r['minimum_setup_ns'],r['minimum_hold_ns'])
'''
compile(q,'cprogress284','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
