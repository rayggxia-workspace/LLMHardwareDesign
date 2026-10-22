import json,hashlib,gzip,zipfile,sys
from pathlib import Path
from collections import Counter
p=Path(sys.argv[1]); rows=json.loads((p/'cases.json').read_text()); static=json.loads((p/'static-choices.json').read_text());
base=[r for r in rows if r['status']=='feasible' and r['config']['key_tile']==16 and r['config']['bank_bytes']==[65536,65536] and r['config']['bank_port_bytes_per_cycle']==64 and not r['disabled_links'] and r['workload'].startswith('observed')]
summary=[]
for ports in ['1RW','1R1W','2RW']:
 for phase in ['observed-prefill32','observed-decode48']:
  a=next(r for r in base if r['config']['bank_ports']==ports and r['workload']==phase and r['placement']==dict(O=0,m=0,l=0)); b=next(r for r in base if r['config']['bank_ports']==ports and r['workload']==phase and r['placement']==dict(O=1,m=1,l=1)); assert a['traffic']==b['traffic']; summary.append(dict(ports=ports,phase=phase,all_B0=a['makespan'],all_B1=b['makespan'],reduction_pct=100*(1-b['makespan']/a['makespan']),cycles_policies_B0=a['policy_cycles'],cycles_policies_B1=b['policy_cycles'],traffic=a['traffic']))
selected=[x for x in static if x['config']['key_tile']==16 and x['config']['bank_port_bytes_per_cycle']==64]
fails=Counter(r['reason'].split(':')[0] if r['reason'].startswith(('capacity','scratch')) else 'missing static link' for r in rows if r['status']=='infeasible')
print(json.dumps(dict(table=summary,failures=dict(fails),static=selected),indent=2))
