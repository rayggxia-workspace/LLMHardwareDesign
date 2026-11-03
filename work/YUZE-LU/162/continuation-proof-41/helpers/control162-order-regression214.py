"""Admit actual source213 ordering regressions on an existing free own slot."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-213';base=b/'s-ready-composition-01/1391';record=b/'route-selection-102/sready214-initial-order-regression';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=json.loads((source/'source-manifest.json').read_text());assert m['commit']=='a11c24dd448ac4a780546ab5cb9a1b8e828220c5'
for name in ['system_geometry.py','system_accept.py','system_sta.py','system_pg_audit.py','system_native_audit.py','upper_rc_network.py','native_stitch.py','boundary_links.py']:
 p='project/experiments/control_v1/'+name;assert m['files'][p]==sha(source/p)==sha(b/'source-172'/p)
baseline=b/'source-211/project/experiments/control_v1/tree_router.cpp';assert sha(baseline)==sha(b/'source-172/project/experiments/control_v1/tree_router.cpp')
previous=b/'router-complete-interface-analysis-212/receipt.json';assert json.loads(previous.read_text())['passed']
queue=b/'dynamic-04/node25';task=queue/'pending/00-j-sready214-order-regression.json';out=b/'router-initial-order-regression-214';assert not task.exists()and not out.exists()
spec=dict(script='system_upper.py',source_root=str(source),forecast_gib=96,requires=[str(previous)],args=list(map(str,['--manifest',base/'selected/physical.json','--graph',base/'topology/boundary-graph.json','--route-regression-only','--route-regression-baseline',baseline,'--out',out])))
record.mkdir();tmp=task.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(task)
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=[dict(path=str(task),sha256=sha(task),spec=spec)],baseline=dict(path=str(baseline),sha256=sha(baseline)),whole_system_qualified=False,scope='Actual new ordering9 fixture routes, all old regression cases, three old-source default route/log byte replays and three impossible budget rejection controls. One already free own16CPU slot on node25, original6x16 queue and memory guard; no other jobs or R touched.'),indent=2))
print(json.dumps(dict(queued=1,out=str(out),whole_system_qualified=False)))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
