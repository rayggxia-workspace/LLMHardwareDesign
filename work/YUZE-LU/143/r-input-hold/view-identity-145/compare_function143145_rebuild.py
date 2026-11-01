import json,sys
from pathlib import Path
base=Path('/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030')
sys.path.insert(0,str(base/'snapshots/144/project/experiments/block_v1'))
from r_function_view_identity_strict import identity as strict
from r_function_view_identity import identity,sha
left=base/'outputs/143/function-r/physical-functional-proof.json'
right=base/'outputs/145/function-r/physical-functional-proof.json'
available=int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemAvailable:')))*1024
assert available>=192*1024**3,available
try:strict(left,right,sha(left))
except AssertionError as error:
 rejection=dict(strict_check_rejected=True,error=str(error),original_proof_sha256=sha(left),selected_proof_sha256=sha(right),strict_helper_sha256=sha(Path(__file__).with_name('r_function_view_identity_strict.py')),qualified=False,native_leaf_accepted=False)
else:raise AssertionError('Expected the real src-metadata difference to be rejected by original checker')
f=base/'outputs/145/view-identity-initial-rejection.json'
assert not f.exists();f.write_text(json.dumps(rejection,indent=2)+'\n')
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
x=identity(left,right,sha(left),lib)
x.update(computation_only=True,qualified=False,native_leaf_accepted=False,helper_sha256=sha(Path(__file__).with_name('r_function_view_identity.py')),liberty_sha256=sha(lib),memory_available_before_bytes=available)
f=base/'outputs/145/view-identity143145.json'
assert not f.exists();f.write_text(json.dumps(x,indent=2)+'\n')
print(json.dumps(x))
