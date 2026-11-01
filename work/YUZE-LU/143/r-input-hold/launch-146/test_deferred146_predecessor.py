import hashlib,json,sys
from pathlib import Path
base=Path('/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030')
root=base/'snapshots/146';out=base/'outputs/146'
f=root/'project/experiments/block_v2/remote_r_deferred_gates.sh'
manifest=json.loads((root/'source-manifest.json').read_text())
sha=hashlib.sha256(f.read_bytes()).hexdigest()
assert sha==manifest['files'][str(f.relative_to(root))]['sha256']
assert not out.exists() and not Path(str(out)+'.predecessor-admission.json').exists()
code=f.read_text().split("<<'PY'\n",1)[1].split('\nPY\n',1)[0]
sys.argv=[str(f),str(root),str(out)]
try:exec(compile(code,str(f)+':metadata-guard','exec'),{'__name__':'__main__'})
except AssertionError as error:
 text=str(error);assert 'RUNNING' in text and ('94507' in text or '94509' in text),text
else:raise AssertionError('Running native predecessor was not refused')
assert not out.exists() and not Path(str(out)+'.predecessor-admission.json').exists()
x=dict(negative_control_passed=True,actual_running_predecessor_refused=True,error=text,source_commit=manifest['commit'],wrapper_sha256=sha,qualified=False,native_leaf_accepted=False,queue_not_created=True,scope='Execute exact source metadata guard against actual running native predecessor; no mocked Slurm success or fabricated receipt, no EDA gate started')
target=base/'outputs/146-predecessor-control.json';assert not target.exists();target.write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
