"""Require byte-identical full route outputs before using the exact BVH."""
from pathlib import Path
import ast,subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-cache-compare143.py');tree=ast.parse(p.read_text(encoding='utf-8'));q=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='q'for t in n.targets)))
for old,new in [('router-congestion-regression-01','router-history-product-regression-01'),('router-exact-cache-regression-01','router-segment-regression-01'),('sready143-exact-cache-comparison.json','sready145-segment-comparison.json'),('source-142','source-144'),('source-143','source-145')]:assert old in q;q=q.replace(old,new)
q=q.replace("if target.exists():print(target.read_text());raise SystemExit(0)","if target.exists():\n d=json.loads(target.read_text());print(json.dumps(dict(passed=d['passed'],identical_successful_route_count=d['identical_successful_route_count'],oracles=len(d['actual_cache_oracles']))));raise SystemExit(0)")
q=q.replace("and d['independent_congestion_impossible_budget_rejected']","and d['independent_congestion_impossible_budget_rejected']and len(d['product_history_cases'])==8 and d['product_history_impossible_budget_rejected']")
q=q.replace('len(outputs)>=128','len(outputs)==140')
q=q.replace("d['exact_cache_and_invalidation_checks']==100500","d['exact_cache_and_invalidation_checks']==100500 and d['exhaustive_segment_grid_checks']==50000 and d['exhaustive_compressed_branch_checks']==50000")
q=q.replace('versus immutable source142, plus','versus immutable source144, including all product-history cases, plus').replace('exact cache invalidation checks actually ran','exact cache invalidation and exhaustive segment/branch XY-union checks actually ran')
compile(q,'exact_segment_comparison','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
