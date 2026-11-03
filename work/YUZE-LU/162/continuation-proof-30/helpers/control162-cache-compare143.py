"""Only compare completed source143 outputs to actual source142 bytes."""
import subprocess,shlex
q=r'''from pathlib import Path
import hashlib,json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');old=b/'router-congestion-regression-01';new=b/'router-exact-cache-regression-01';target=b/'route-selection-102/sready143-exact-cache-comparison.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if target.exists():print(target.read_text());raise SystemExit(0)
receipt=new/'receipt.json'
if not receipt.exists():print(json.dumps(dict(ready=False,actual_case_folders=len(list(new.glob('case-*'))),actual_cache_distance_oracles=len(list(new.rglob('router-distance-oracle.json'))))));raise SystemExit(0)
for p in [old,new]:
 r=json.loads((p/'receipt.json').read_text());assert r['passed']and r['outputs']['router-search-regression.json']==sha(p/'router-search-regression.json')
 d=json.loads((p/'router-search-regression.json').read_text());assert d['passed']and len(d['cases'])==120 and len(d['independent_congestion_cases'])==8 and d['independent_congestion_impossible_budget_rejected']
for root,source in [(old,'source-142'),(new,'source-143')]:
 r=json.loads((root/'receipt.json').read_text())
 for name in ['router_regression.py','tree_router_cpp.py','tree_router.cpp']:
  path=b/source/'project/experiments/control_v1'/name;assert r['inputs'][str(path)]==sha(path)
outputs={str(p.relative_to(old))for p in old.rglob('router-output.txt')};new_outputs={str(p.relative_to(new))for p in new.rglob('router-output.txt')};assert outputs==new_outputs and len(outputs)>=128
rows=[]
for relative in sorted(outputs):
 a=old/relative;z=new/relative;inp=a.with_name('router-input.txt');new_inp=z.with_name('router-input.txt')
 assert sha(inp)==sha(new_inp)and a.read_bytes()==z.read_bytes(),relative
 rows.append(dict(relative_output=relative,identical_input_sha256=sha(inp),identical_route_output_sha256=sha(a),bytes=a.stat().st_size))
oracles=[]
for p in sorted(new.rglob('router-distance-oracle.json')):
 d=json.loads(p.read_text());assert d['passed']and d['exhaustive_distance_checks']==50000 and d['exact_cache_and_invalidation_checks']==100500;oracles.append(dict(path=str(p),sha256=sha(p)))
assert len(oracles)>=len(outputs)
d=dict(time=time.time(),passed=True,whole_system_qualified=False,old_receipt_sha256=sha(old/'receipt.json'),new_receipt_sha256=sha(new/'receipt.json'),identical_successful_route_count=len(rows),identical_routes=rows,actual_cache_oracles=oracles,scope='Every successful full-regression route has identical input and byte-identical output versus immutable source142, plus independent edge/flood/short and all original negative budget/overlap tests; exact cache invalidation checks actually ran. No full-scene convergence or hardware qualification inferred.')
target.write_text(json.dumps(d,indent=2));print(json.dumps(dict(passed=True,identical_successful_route_count=len(rows),oracles=len(oracles),record=str(target))))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
