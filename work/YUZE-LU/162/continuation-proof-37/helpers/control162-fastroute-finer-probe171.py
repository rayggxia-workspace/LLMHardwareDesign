"""Append one finer-guide probe in the already released own node4 slot."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');base=b/'s-ready-composition-01/1391';source=b/'source-171';queue=b/'dynamic-05/node4';record=b/'route-selection-102/sready171-fastroute24um-probe.json';assert not record.exists()
m=json.loads((source/'source-manifest.json').read_text());assert m['commit']=='dec7777417befc91a464cf94b0b528ce9ade4c41'
assert json.loads((b/'router-fastroute-preflight-170/receipt.json').read_text())['passed']is False
log=(b/'router-fastroute-preflight-170/case-0/openroad.log').read_text();assert'GRT-0228'not in log and'GRT-0116'in log
state=json.loads((queue/'queue-state.json').read_text());assert len(state['active'])<=3
f=queue/'pending/00-j-sready171-fastroute24um-probe.json';out=b/'router-fastroute24-preflight-171';assert not f.exists()and not out.exists()
a=['--manifest',base/'selected/physical.json','--graph',base/'topology/boundary-graph.json','--openroad-router-probe-only','--openroad-global-router','fastroute','--openroad-guide-pitch-um',1.6,'--openroad-congestion-iterations',50,'--out',out]
spec=dict(script='system_upper.py',source_root=str(source),forecast_gib=32,requires=[str(base/'topology/receipt.json')],args=list(map(str,a)))
temp=f.with_suffix('.tmp');temp.write_text(json.dumps(spec));temp.rename(f)
record.write_text(json.dumps(dict(time=time.time(),path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),source_manifest_sha256=hashlib.sha256((source/'source-manifest.json').read_bytes()).hexdigest(),reason='Actual corrected60um FastRoute no longer hits resource0, but original crossing fixture still has heuristic global overflow and is rejected. Compare24um global guide tiles via unused/unroutable lower search track grids1.6um. Native technology unchanged, actual M11/M12 pitch4um and all original independent geometry/PG/RC gates unchanged; no allow_congestion, no tool patch, no extra node/cancellation. Full three-case fixture and9 negative parser controls mandatory, never system qualification.'),indent=2))
print('Appended actual24um FastRoute probe in existing own slot')
'''
compile(q,'fine_global_guide_probe171','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
