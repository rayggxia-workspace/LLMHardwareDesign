from pathlib import Path
import json,sys,hashlib
from native_macro_graph import Frontend
from native_macro_select import select
root=Path(__file__).resolve().parents[1];out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=False)
sources=list((root/'compiler').glob('native_*range*.py'))+[root/'compiler/native_macro_select.py',root/'compiler/native_resident_binding_search.py']
(out/'source-receipt.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},indent=2)+'\n')
for phase in ('prefill','decode'):
 directory=Path(sys.argv[1])/phase
 receipt=json.loads((root/('evidence/architecture-revision-185/shared-memory-graphs-114904/'+phase+'-candidates/source-receipt.json')).read_text())
 paths=[next(k for k in receipt['inputs'] if k.endswith(n)) for n in ('native-recipe-graph.json','native-operand-recipes.json','native-value-layout.json')]
 f=Frontend(*[json.loads((root/p).read_text()) for p in paths],
  json.loads((root/'hardware/blockv2-mod-shared-memory.json').read_text()),
  json.loads((root/'hardware/service-controller-contracts.json').read_text())['services'],18503,range_tiles=8)
 p=select(f,directory/'candidates',width=8,progress=lambda x:print(phase,x,flush=True))
 target=out/phase;target.mkdir()
 (target/'plan.json').write_text(json.dumps(p,separators=(',',':'))+'\n')
 print(json.dumps({'phase':phase,'calls':len(p['calls']),'tasks':len(p['selection']),'elisions':sum(len(x['elisions']) for x in p['residency'])}),flush=True)
