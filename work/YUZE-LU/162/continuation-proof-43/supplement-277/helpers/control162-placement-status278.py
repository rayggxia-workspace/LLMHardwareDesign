import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');p=b/'r256-placement-regression-277/receipt.json';print('placement regression',json.loads(p.read_text()) if p.exists() else'unfinished')
f=b/'r256-early-electrical-266/initial/wire-cap-lower-bound.json';rows=json.loads(f.read_text())['rows'];rr=[r for r in rows if r['driver']['instance']=='macro_r'];print('R output lower bound',dict(nets=len(rr),max_high_ratio=max(max(r['wire_capacitance_lower_bound_ff'].values())/r['physical_driver']['max_capacitance_ff']for r in rr),any_rotation_anyplacement_failures=sum(r.get('any_rotation_any_placement_low_variant_violates',False)for r in rr)))
for n in ['initial','optimized']:
 p=b/'r256-early-electrical-277'/n/'receipt.json'
 if p.exists():print('early277',n,json.loads(p.read_text()).get('passed'))
s=json.loads((b/'dynamic-07/node7/queue-state.json').read_text());print('active',s['active'],'age',time.time()-s['time'])
'''
compile(q,'status278','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
