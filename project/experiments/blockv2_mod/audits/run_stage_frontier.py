from pathlib import Path
import json,sys,hashlib
from native_macro_graph import Frontend
from native_joint_search import select
root=Path(__file__).resolve().parents[1];out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
hardware=json.loads((root/'hardware/blockv2-mod-shared-memory.json').read_text())
services=json.loads((root/'hardware/service-controller-contracts.json').read_text())['services']
source={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'compiler').glob('native_*.py')}
(out/('sources-'+str(__import__('time').time_ns())+'.json')).write_text(json.dumps(source,indent=2)+'\n')
for phase in ('decode',):
 old=root/'evidence/architecture-revision-185/shared-memory-graphs-114904'/(phase+'-candidates/source-receipt.json')
 receipt=json.loads(old.read_text())
 paths=[next(k for k in receipt['inputs'] if k.endswith(n)) for n in ('native-recipe-graph.json','native-operand-recipes.json','native-value-layout.json')]
 data=[json.loads((root/p).read_text()) for p in paths]
 f=Frontend(*data,hardware,services,18503,range_tiles=1,joint=True,independent_ranges="--independent-ranges" in sys.argv)
 directory=out/phase
 if not (directory/'candidates/manifest.json').exists():
  f.export(directory/'candidates',progress=lambda x:print(phase,x,flush=True))
 exports=set(data[0]['outputs'])
 if phase=='prefill':
  bridge=json.loads((root/'evidence/architecture-revision-185/phase-state-bridge-115046.json').read_text())
  exports.update(s['source_root'] for s in bridge['states'].values())
 p=select(f,directory/'candidates',depth=2,width=4,exports=exports,stage_resources=True,diverse=True,objective='finish_proxy',cost_model='service-payload/2' if '--service-payload' in sys.argv else 'structural/1',progress=lambda x:print(phase,x,flush=True))
 p['exported_values']=sorted(exports)
 from native_joint_search import digest
 p.pop('plan_sha256');p['plan_sha256']=digest(p)
 (directory/'plan.json').write_text(json.dumps(p,separators=(',',':'))+'\n')
 print(json.dumps({'phase':phase,'calls':len(p['calls']),'search':p['search_plan']}),flush=True)
