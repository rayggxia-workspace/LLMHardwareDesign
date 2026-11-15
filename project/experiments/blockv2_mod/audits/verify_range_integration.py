from pathlib import Path
import json,sys,hashlib
from native_macro_graph import Frontend
from native_macro_select import select
ROOT=Path(__file__).resolve().parents[1]
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
hardware=json.loads((ROOT/'hardware/blockv2-mod-shared-memory.json').read_text())
services=json.loads((ROOT/'hardware/service-controller-contracts.json').read_text())['services']
results=[]
for phase in ('prefill','decode'):
 receipt=json.loads((ROOT/('evidence/architecture-revision-185/shared-memory-graphs-114904/'+phase+'-candidates/source-receipt.json')).read_text())
 paths=[next(k for k in receipt['inputs'] if k.endswith(n)) for n in ('native-recipe-graph.json','native-operand-recipes.json','native-value-layout.json')]
 data=[json.loads((ROOT/p).read_text()) for p in paths]
 f=Frontend(*data,hardware,services,18503,range_tiles=8)
 directory=out/phase
 f.export(directory/'candidates',progress=lambda x:print(phase,x,flush=True))
 p=select(f,directory/'candidates',width=8,progress=lambda x:print(phase,x,flush=True))
 (directory/'plan.json').write_text(json.dumps(p,separators=(',',':'))+'\n')
 row={'phase':phase,'tasks':len(p['selection']),'calls':len(p['calls']),'plan_sha256':p['plan_sha256'],
      'elided_loads':sum(len(r['elisions']) for r in p['residency'])}
 results.append(row);print(json.dumps(row),flush=True)
(out/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
