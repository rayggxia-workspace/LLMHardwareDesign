from pathlib import Path
from collections import Counter
import json,sys
from native_macro_work import measure
root=Path(__file__).resolve().parents[1];directory=Path(sys.argv[1])
rows=[]
for phase in ('prefill','decode'):
 p=json.loads((directory/phase/'plan.json').read_text())
 old=json.loads((root/'evidence/architecture-revision-185/shared-memory-graphs-114904'/(phase+'-plan/plan.json')).read_text())
 for key in ('graph_sha256','hardware','storage'):
  if p[key]!=old[key]:raise ValueError('baseline input differs '+key)
 def traffic(plan):
  total=Counter()
  for call in plan['calls']:
   cost=measure({'calls':[dict(call,index=0,after=[])]})
   for key in ('ddr_read_bytes_upper','ddr_write_bytes','descriptor_bytes'):total[key]+=cost[key]
   schema=int.from_bytes(bytes.fromhex(call['descriptor_hex'])[:4],'little')
   if schema==0x314c5244:total['explicit_DRL_bytes']+=512
   if schema==0x31535744:total['explicit_DWS_bytes']+=512
  return dict(total)
 operations=Counter();dirty_releases=0
 for step in p['dirty_lifecycle']:
  for e in step['events']:
   operations[e['op']]+=1
   if e['op']=='release' and e['dirty']:dirty_releases+=1
 rows.append({'phase':phase,'plan_sha256':p['plan_sha256'],'ranges':len(p['selection']),
  'calls':len(p['calls']),'baseline_calls':len(old['calls']),
  'traffic':traffic(p),'baseline_traffic':traffic(old),'lifecycle':dict(operations),
  'dirty_releases_without_writeback':dirty_releases,'exported_values':p['exported_values'],
  'timing_calibrated':False,'numeric_execution_pending':True})
(directory/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows))
