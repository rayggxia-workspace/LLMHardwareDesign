"""Admit full cache regression by retiring one exact own obsolete route."""
from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-halo-slots142.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope)
q=scope['q'].replace('sready142-two-obsolete-node5-retired','sready143-cache-regression-old933-retired').replace('for seed in [917,918]:','for seed in [933]:')
q=q[:q.index("\nprint('Released two exact own steps'")]
q=q.replace('Two exact own old335 external-S searches retired only after actual selected235 function and all three halo native/pin necessary bounds passed and21 new route/acceptance tasks appended. Preserve old specs/partial results, all parent allocations, third old933 control, R and all other tasks. Not completed physical failures.',
            'One exact own obsolete old335 external-S search retired for full actual source143 cache regression. Actual selected235 function and three real new halo routes already admitted. Preserve all old specs/partial results, parent allocations, R and all other work. No physical failure/qualification inferred.')
q+=r'''
source=b/'source-143';assert json.loads((source/'source-manifest.json').read_text())['commit']=='3bd63af4f4e83b6148bfb69d25a676ff23b875ab'
for name in ['system_upper.py','tree_router_cpp.py','router_regression.py','system_geometry.py','system_accept.py','system_sta.py','system_pg_audit.py']:
 assert sha(source/'project/experiments/control_v1'/name)==sha(b/'source-142/project/experiments/control_v1'/name)
p=queue/'pending/00-r-sready143-exact-cache-regression.json';out=b/'router-exact-cache-regression-01';assert not p.exists()and not out.exists()
spec=dict(script='system_upper.py',source_root=str(source),forecast_gib=32,requires=[str(c/'topology/receipt.json')],args=list(map(str,['--manifest',c/'selected/physical.json','--graph',c/'topology/boundary-graph.json','--route-regression-only','--out',out])))
t=p.with_suffix('.tmp');t.write_text(json.dumps(spec));t.rename(p);(root/'new-regression-task.json').write_text(json.dumps(dict(path=str(p),sha256=sha(p),spec=spec,source_manifest_sha256=sha(source/'source-manifest.json'),scope='Full128-case actual routing and independent edge/flood/short checks, followed by exact byte comparison to all prior source142 successful routes. Cache must not alter outputs; no new real candidate admitted from source143 until verified.'),indent=2));print('Appended full source143 exact-cache regression; retired',stopped)
'''
compile(q,'actual_cache_regression_admission','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
