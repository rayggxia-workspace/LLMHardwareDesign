"""Materialize BOTH plans against a single selected wiring union."""
import json,sys
from pathlib import Path
from native_selected_endpoint_bindings import build
from native_static_wiring_union import merge
from materialize_native_product import materialize
from native_machine_package import package
plans,out,hardware=map(Path,sys.argv[1:4]);mode=sys.argv[4]
p=[json.loads((plans/str(h)/'plan.json').read_text()) for h in (512,513)]
if p[0]['hardware']!=p[1]['hardware']:raise ValueError('different bases')
if mode=='prepare':
 out.mkdir(parents=True,exist_ok=False)
 (out/'selected.json').write_text(json.dumps(merge([build(x) for x in p]),indent=2)+'\n')
else:
 wiring=materialize(p,out/'product',hardware,mode)
 for h,plan in zip((512,513),p):package(plan,out/f'{h}-package',18503,wiring)
