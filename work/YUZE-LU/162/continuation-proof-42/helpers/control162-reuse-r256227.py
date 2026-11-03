"""Import PR168 exact tested objects into this worktree only; no PR merge."""
from pathlib import Path
import subprocess,json,hashlib
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');revision='55f2553bdacbca971b1505a11675a0b1eb12fcad'
def read(name):return subprocess.check_output(['git','show',revision+':'+name],cwd=repo)
inputs_name='work/YUZE-LU/162/r256-integration-20261103/INPUTS-05.json';inputs=json.loads(read(inputs_name));assert len(inputs)==48
changed=[]
for name,digest in inputs.items():
 data=read(name);assert hashlib.sha256(data).hexdigest()==digest
 p=repo/name
 if not p.exists()or p.read_bytes()!=data:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);changed.append(name)
extra=['docs/CONTROL_R256_INTEGRATION.md',inputs_name,'work/YUZE-LU/162/r256-integration-20261103/LOCAL_RECEPTION.json']
prefix='work/YUZE-LU/162/r256-integration-20261103/evidence-05/'
names=subprocess.check_output(['git','ls-tree','-r','--name-only',revision,'--',prefix],cwd=repo).decode().splitlines()
extra+=names
for name in extra:
 data=read(name);p=repo/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
receipt=json.loads(read(prefix+'results/RECEIPT.json'));assert receipt['rtl_integration_passed']and len(receipt['cases'])==99 and all(c['passed']and c['exit_code']==0 for c in receipt['cases'])
for case in receipt['cases']:
 relative='results/'+case['model']+'/i'+str(case['initialization'])+'-s'+str(case['seed'])+'.log';data=read(prefix+relative);assert hashlib.sha256(data).hexdigest()==case['log_sha256']
out=repo/'work/YUZE-LU/162/r256-reuse227';assert not out.exists();out.mkdir()
(out/'reuse.json').write_text(json.dumps(dict(source_pr=168,source_commit=revision,head_readback='4f1a383049de5efa472f020e352c86be8c308614',tested_inputs=inputs,changed=changed,inherited_test_cases=99,all_inherited_case_log_bytes_verified=True,imported_evidence_files=len(extra),draft226_superseded=True,draft226_never_queued=True,no_other_worktree_or_job_modified=True,physical_and_system_qualified=False,scope='Reuse exact already tested R256 interface and real seven-macro programs. Default physical baseline235 searches remain immutable; new adapter and new parameter configurations require new full backend. No GitHub PR or main merged.'),indent=2)+'\n')
print(json.dumps(dict(imported_tested_inputs=len(inputs),changed=len(changed),inherited_logs_verified=99,physical_qualified=False)))
