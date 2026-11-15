from pathlib import Path
import json
from collections import Counter
from native_macro_work import measure
for phase in ('prefill','decode'):
 p=json.loads((Path('evidence/architecture-revision-185/shared-memory-graphs-114904')/(phase+'-plan/plan.json')).read_text())
 cost=Counter()
 for c in p['calls']:
  row=measure({'calls':[dict(c,index=0,after=[])]})
  for key in ('ddr_read_bytes_upper','ddr_write_bytes'):cost[key]+=row[key]
 print(phase,dict(cost),flush=True)
