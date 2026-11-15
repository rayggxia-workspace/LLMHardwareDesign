from pathlib import Path
import json,sys,os
from native_selected_endpoint_bindings import build
from native_static_wiring_union import merge
from materialize_native_product import materialize
from native_machine_package import package
root=Path(__file__).resolve().parents[1];plans=Path(sys.argv[1]);out=Path(sys.argv[2])
p=[json.loads((plans/phase/'plan.json').read_text()) for phase in ('prefill','decode')]
if sys.argv[3]=='prepare':
 out.mkdir(parents=True,exist_ok=False)
 (out/'selected.json').write_text(json.dumps(merge([build(x) for x in p]),indent=2)+'\n')
else:
 wiring=materialize(p,out/'product',root/'hardware/blockv2-mod-shared-memory.json',sys.argv[3])
 for phase,plan in zip(('prefill','decode'),p):
  package(plan,out/(phase+'-package'),18503,wiring)
  old=root/'evidence/architecture-revision-185/shared-memory-bound-packages-114908'/(phase+'-package')
  old_storage=json.loads((old/'storage.json').read_text())
  if old_storage!=plan['storage']:raise ValueError('range transform changed allocation; rematerialize inputs')
 print('same-plan packages and unchanged input allocations verified',flush=True)
