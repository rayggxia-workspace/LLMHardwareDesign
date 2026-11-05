"""Retire one exact same-placement lower-effort control after actual phase failure."""
from pathlib import Path
import ast,subprocess,shlex

p=Path(r'D:\Data\电路实验\control162-snapshot-preflight180.py');tree=ast.parse(p.read_text(encoding='utf-8'));q=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='q'for t in n.targets)))
q=q[:q.index("fixture=b/'router-fastroute24phase-preflight-172'")]
for a,b in [("source=b/'source-180'","source=b/'source-172'"),('dynamic-05/node2','dynamic-05/node4'),('sready180-bounded-snapshot','sready186-duplicate1514-phase-refill'),('3f4ee5dc09e43bb8066e1266fd44227387c29ae9','9c16b78b7430f636b7833106483da95ef8307232'),('sready140-route-1410','sready156openroad-route-1514'),("str(b/'source-140')","str(b/'source-156')"),('upper-candidates/1410/route','upper-candidates/1514/route'),('job=95341','job=95391'),('NodeList=node2 ','NodeList=node4 '),("b/'source-140/project/experiments/control_v1/system_upper.py'","b/'source-156/project/experiments/control_v1/system_upper.py'"),("targets[0]['host']=='node2'","targets[0]['host']=='node4'")]:
    assert a in q,a;q=q.replace(a,b)
q+=r'''
assert args[args.index('--router')+1]=='openroad'
control=queue/'pending/00-k-sready157openroad-route-1515.json';cs=json.loads(control.read_text());ca=cs['args'];assert ca[ca.index('--reuse-placement')+1]==args[args.index('--reuse-placement')+1]and ca[ca.index('--openroad-congestion-iterations')+1]=='50'
assert control.stem in state['active']
pending=queue/'pending/00-j-sready178-cugr24um-phase-probe.json';ns=json.loads(pending.read_text());na=ns['args'];assert ns['source_root']==str(source)and ns['script']=='system_upper.py'and na[na.index('--openroad-global-router')+1]=='cugr'and float(na[na.index('--openroad-guide-pitch-um')+1])==1.6
snapshot=b/'router-full-cugr-snapshot-181';sr=json.loads((snapshot/'receipt.json').read_text());sd=json.loads((snapshot/'snapshot.json').read_text());assert sr['passed']and sr['outputs']['snapshot.json']==sha(snapshot/'snapshot.json')and not sd['actual_router_drc_empty']and 'Off-grid X'in sd['independent_original_grid_check']['error']
rawlog=(snapshot/'openroad.log').read_bytes();assert b'Number of violations = 950442'in rawlog
record.mkdir();logs={}
for seed in [1514,1515]:
 p=base/'upper-candidates'/str(seed)/'route/openroad-search/case-0/openroad.log';data=p.read_bytes();logs[str(p)]=dict(bytes=len(data),prefix_sha256=hashlib.sha256(data).hexdigest(),violation_rounds=re.findall(r'Number of violations = (\d+)',data.decode()),tail=data.decode().splitlines()[-8:])
reason='Retire only own incomplete CUGR60um effort5 duplicate1514; keep same exact1474 placement effort50 control1515, original1513 and all other comparisons. Actual bound replay181 independently rejects old60um guide route net10 X2280000DBU versus required190mod8000, with950442 actual violations; not a final1514 failure or a waiver. The immutable source172 CUGR24um phase190/140 probe178 is already queued before retiring child, so it dynamically fills the released16CPU slot. All original specs/partials and parents/R/other jobs preserved.'
(record/'verified-before.json').write_text(json.dumps(dict(time=time.time(),target=targets[0],old_spec=str(old),old_spec_sha256=sha(old),job_details=details,queue_state=state,retained_same_placement_control=str(control),control_spec_sha256=sha(control),queued_probe=str(pending),queued_probe_sha256=sha(pending),actual_snapshot_receipt_sha256=sha(snapshot/'receipt.json'),actual_snapshot_report_sha256=sha(snapshot/'snapshot.json'),active_log_prefix_snapshots=logs,reason=reason),indent=2))
subprocess.run(['scancel',targets[0]['step']],check=True)
(record/'cancelled.json').write_text(json.dumps(dict(time=time.time(),step=targets[0]['step'])))
print('Retired only same-placement lower-effort own child',targets[0]['step'],'for already queued phase-correct probe; retained1515')
'''
compile(q,'exact_1514_phase_refill186','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
