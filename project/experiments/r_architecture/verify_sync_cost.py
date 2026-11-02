"""Independent accounting check over two actually executed, matched RTL controls."""
from pathlib import Path
import csv, hashlib, json
R=Path(__file__).resolve().parents[3]
D=R/'work/YUZE-LU/157';E=D/'smallcap-runs'
def load(name):return json.loads((E/name).read_text(encoding='utf-8'))
old=load('async081-results.json');new=load('sync074-results.json')
assert len(old)==len(new)==48
fields=['workload','policy','latency','bandwidth']
index={tuple(r[k]for k in fields):r for r in old};assert len(index)==48
builds=[load('async081-build.json'),load('sync074-build.json')]
assert builds[0]['read_latency_cycles']==0 and builds[1]['read_latency_cycles']==2
unit=load('sync071-receipt.json');checks=load('sync071-functional.json')
assert unit['passed'] and unit['mapped'] and unit['corpus_cases']==len(checks)==63
assert all(r['passed']for r in checks)
assert unit['checks']==sum(r['checks']for r in checks)==28174656
rows=[]
for r in new:
 b=index[tuple(r[k]for k in fields)]
 assert b['status']==r['status']=='PASS' and b['exit']==r['exit']==0
 assert b['input_sha256']==r['input_sha256']
 assert b['binary_sha256']==builds[0]['binary_sha256']
 assert r['binary_sha256']==builds[1]['binary_sha256']
 for k in ['DRAM_read_bytes','DRAM_write_bytes','S_allocated_peak','commits','aborts',
           'R_wide_mul_events','traffic','ports']:
  assert b[k]==r[k],(r['workload'],r['policy'],k)
 extra=r['cycles']-b['cycles'];assert extra==b['stages'].get('R_read',0)
 for k in set(b['stages'])|set(r['stages']):
  assert r['stages'].get(k,0)-b['stages'].get(k,0)==(extra if k=='R_read'else 0)
 rows.append(dict(workload=r['workload'],policy=r['policy'],async_cycles=b['cycles'],
  sync_cycles=r['cycles'],extra_cycles=extra,increase_percent=100*extra/b['cycles'],
  input_sha256=r['input_sha256']))
with(D/'SYNC_READ_COST.csv').open('w',newline='',encoding='utf-8')as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
sources=['async081-results.json','sync074-results.json','async081-build.json',
         'sync074-build.json','sync071-receipt.json','sync071-functional.json']
(D/'SYNC_READ_VALIDATION.json').write_text(json.dumps(dict(passed=True,matched_pairs=48,
 unit_cases=63,unit_checks=28174656,extra_cycles_exactly_one_per_serial_read=True,
 no_new_physical_qualification=True,inputs_sha256={name:hashlib.sha256((E/name).read_bytes()).hexdigest()for name in sources}),indent=2)+'\n',encoding='utf-8')
print('PASS:48 matched RTL/SystemC pairs;63 unit cases;28,174,656 checks; no physical qualification')
