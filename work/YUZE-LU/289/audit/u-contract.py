"""Audit exact unchanged engineering SDC and selected output load values."""
from pathlib import Path
import sys,re,json,hashlib
run=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
p=next((run/'flow/results/nangate45').glob('*/*'))/'6_final.sdc'
ref=root/'cu/runs/U-v7-macropdn-x8-seed0/flow/results/nangate45/u-overlay-current/base/6_final.sdc'
normalize=lambda p:[l.strip() for l in p.read_text().splitlines() if l.strip() and not l.lstrip().startswith('#')]
a,b=normalize(ref),normalize(p);assert a==b,'Timing contract changed since U-v7'
selected=set((root/'cu/U-outputs.txt').read_text().splitlines());assert len(selected)==153
loads=dict((n,float(v)) for v,n in re.findall(r'^set_load -pin_load ([\d.]+) \[get_ports \{(.*?)\}\]',p.read_text(),re.M))
assert selected<=loads.keys();assert all(loads[x]==50 for x in selected)
assert all(v==2 for n,v in loads.items() if n not in selected)
assert 'create_clock -name clk -period 4.0000 [get_ports {clk_i}]' in b
assert 'set_clock_uncertainty 0.1000 clk' in b
assert not any(l.startswith(('set_false_path','set_multicycle_path','set_disable_timing')) for l in b)
r=dict(passed=True,source=str(ref),candidate=str(p),noncomment_contract_exact=True,selected_output_count=len(selected),selected_load_fF=50,other_output_load_fF=2,period_ns=4,uncertainty_ns=.1,scope='New engineering standalone IO contract; not actual top RC/PVT signoff',hashes={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in (ref,p)})
(out/'sdc-contract.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
