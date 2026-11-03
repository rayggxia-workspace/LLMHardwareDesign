from pathlib import Path
import subprocess,shlex,json,hashlib,base64
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');h=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-58';d=json.loads((out/'index.json').read_text(encoding='utf-8'));assert'pending_flex_supplement'not in d
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();gates={}
for n in ['system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py','resource_search.h','r256_scene.py']:
 a=b/'source-474/project/experiments/control_v1'/n;p=b/'source-537/project/experiments/control_v1'/n;assert sha(a)==sha(p);gates[n]=sha(p)
p=b/'route-selection-102/sready569-pending-c96-flexibility/receipt.json';raw=p.read_bytes();assert json.loads(raw)['passed'];print(json.dumps(dict(time=time.time(),relative='pending-flex-supplement/receipt.json',path=str(p),bytes=len(raw),sha256=sha(p),base64=base64.b64encode(raw).decode(),unchanged_source474_vs537_gate_and_scene_sha256=gates,whole_system_qualified=False)))
'''
s=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));raw=base64.b64decode(s.pop('base64'));assert hashlib.sha256(raw).hexdigest()==s['sha256'];p=out/s['relative'];p.parent.mkdir();p.write_bytes(raw);d['helpers'].append(dict(relative=s['relative'],bytes=len(raw),sha256=s['sha256']));d['pending_flex_supplement']=s
for n in ['flex569','flex569-remote','bind570']:
 p=h/('control162-'+n+'.py');raw=p.read_bytes();rel='helpers/'+p.name;assert not(out/rel).exists();(out/rel).write_bytes(raw);d['helpers'].append(dict(relative=rel,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(passed=True,unchanged_gates=len(s['unchanged_source474_vs537_gate_and_scene_sha256']),rows=len(d['rows']),helpers=len(d['helpers']))))
