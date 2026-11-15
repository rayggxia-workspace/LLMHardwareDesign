from pathlib import Path
import sys,json,copy
ROOT=Path.cwd();sys.path[:0]=[str(ROOT/'compiler'),str(ROOT/'hardware')]
from native_macro_graph import Frontend
from native_selected_endpoint_bindings import build
from native_static_wiring_union import merge
from native_package_runtime import load
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
hw=json.loads((ROOT/'hardware/blockv2-mod-macros.json').read_text())
services=json.loads((ROOT/'hardware/service-controller-contracts.json').read_text())['services']
rows=[];bindings=[]
for stage,graphdir in [('prefill','two-input-114228'),('decode','two-input-114287')]:
 base=ROOT/'evidence'/graphdir
 data=[json.loads((base/n).read_text()) for n in ('native-recipe-graph.json','native-operand-recipes.json','native-value-layout.json')]
 frontend=Frontend(*data,hw,services,18503)
 tasks=0;options=0
 for task in frontend.tasks.values():
  if task['kind']=='View':continue
  opts=frontend.options(task);assert opts
  tasks+=1;options+=len(opts)
 plan=json.loads((ROOT/'evidence/architecture-revision-185/macro-selection-114823'/stage/'plan.json').read_text())
 b=build(plan);bindings.append(b)
 manifest,payload,pages=load(ROOT/'evidence/architecture-revision-185/macro-package-114824'/(stage+'-package'))
 assert manifest['plan_sha256']==plan['plan_sha256']
 assert manifest['native_calls']==len(plan['calls'])
 assert json.loads(payload['hardware.json'])==plan['hardware']
 rows.append({'stage':stage,'graph_tasks':tasks,'candidate_options':options,
  'sealed_native_calls':manifest['native_calls'],'MC_pages':len(pages),'plan_sha256':plan['plan_sha256']})
union=merge(bindings)
bad=copy.deepcopy(bindings[0]);bad['connections'][0]['driver']='invented.other_driver'
try:merge([bindings[0],bad])
except ValueError:pass
else:raise AssertionError('phase-specific contradictory metal was accepted')
(out/'static-product-wiring.json').write_text(json.dumps(union,indent=2)+'\n')
result={'graphs':rows,'negative_static_multi_driver':True,'known_connections':len(union['connections']),
 'unresolved_interfaces':len(union['unresolved']),'whole_base_accepted':False,'TLM_executed':False}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
