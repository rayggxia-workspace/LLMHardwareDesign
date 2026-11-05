"""Join actual product regression and exact default compatibility evidence."""
import subprocess,shlex
q=r'''from pathlib import Path
import hashlib,json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');old=b/'router-exact-cache-regression-01';new=b/'router-history-product-regression-01';target=b/'route-selection-102/sready144-history-product-comparison.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
if target.exists():
 d=json.loads(target.read_text());print(json.dumps(dict(passed=d['passed'],identical_default_routes=d['identical_default_routes'],independent_product_cases=d['independent_product_cases'],record=str(target))));raise SystemExit(0)
r=new/'receipt.json'
if not r.exists():print(json.dumps(dict(ready=False,case_folders=len(list(new.glob('case-*'))),product_folders=len(list(new.glob('product-history-*'))))));raise SystemExit(0)
receipt=json.loads(r.read_text());assert receipt['passed'],receipt.get('error')
for folder,source in [(old,'source-143'),(new,'source-144')]:
 d=json.loads((folder/'receipt.json').read_text());assert d['passed']and d['outputs']['router-search-regression.json']==sha(folder/'router-search-regression.json')
 for name in ['router_regression.py','tree_router_cpp.py','tree_router.cpp']:
  p=b/source/'project/experiments/control_v1'/name;assert d['inputs'][str(p)]==sha(p)
report=json.loads((new/'router-search-regression.json').read_text());assert len(report['cases'])==120 and len(report['independent_congestion_cases'])==8 and len(report['product_history_cases'])==8 and report['product_history_impossible_budget_rejected']
before={str(p.relative_to(old))for p in old.rglob('router-output.txt')};after={str(p.relative_to(new))for p in new.rglob('router-output.txt')};assert len(before)==132 and before<=after and len(after-before)==8
rows=[]
for relative in sorted(before):
 a=old/relative;z=new/relative;aa=a.with_name('router-input.txt').read_bytes();zz=z.with_name('router-input.txt').read_bytes();ah,ab=aa.split(b'\n',1);zh,zb=zz.split(b'\n',1)
 assert zh.split()[:-1]==ah.split()and zh.split()[-1]==b'0'and ab==zb and a.read_bytes()==z.read_bytes(),relative
 rows.append(dict(path=relative,old_input_sha256=hashlib.sha256(aa).hexdigest(),new_input_sha256=hashlib.sha256(zz).hexdigest(),identical_output_sha256=sha(a)))
for proof in report['product_history_cases']:assert proof['multiplicative_congestion_history']and proof['final_conflicts']==0 and proof['independent_tree_flood']and proof['independent_cross_net_occupancy']
d=dict(time=time.time(),passed=True,whole_system_qualified=False,identical_default_routes=132,independent_product_cases=8,new_receipt_sha256=sha(r),old_receipt_sha256=sha(old/'receipt.json'),default_compatibility=rows,scope='Only a new explicit trailing zero history-mode option is normalized on legacy headers; every net/terminal/budget and all132 default route outputs remain exact. Eight product searches independently pass complete edge/flood/short tests and impossible wire budget rejected. No actual full-scene convergence/timing claim.')
target.write_text(json.dumps(d,indent=2));print(json.dumps(dict(passed=True,identical_default_routes=132,independent_product_cases=8,record=str(target))))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
