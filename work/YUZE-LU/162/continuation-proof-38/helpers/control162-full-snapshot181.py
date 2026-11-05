"""Replay original full CUGR scene for concrete short locations without changing it."""
import subprocess,shlex

q=r'''from pathlib import Path
import json,hashlib,re,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');base=b/'s-ready-composition-01/1391';source=b/'source-180';queue=b/'dynamic-05/node2';record=b/'route-selection-102/sready181-full-cugr-snapshot.json';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
probe=b/'router-bounded-snapshot-preflight-180';r=json.loads((probe/'receipt.json').read_text());d=json.loads((probe/'snapshot.json').read_text())
assert r['passed']and r['stage']=='bounded-routing-diagnostic-only'and d['actual_router_drc_empty']and d['independent_original_grid_check']['passed']and not d['whole_system_qualified']
assert r['outputs']['snapshot.json']==sha(probe/'snapshot.json')
for n in ['system_upper.py','openroad_snapshot.py','openroad_grid.py']:
 p=source/'project/experiments/control_v1'/n;assert r['inputs'][str(p)]==sha(p)
folder=base/'upper-candidates/1513/route/openroad-search/case-0';tcl=(folder/'run.tcl').read_text();dims=re.search(r'set die \[odb::new_Rect 0 0 (\d+) (\d+)\]',tcl);assert dims
width,height=map(int,dims.groups());assert width%8000==height%8000==0
terminals=json.loads((folder/'terminals.json').read_text());assert len(terminals)==8990
assert 'Number of violations = 561152'in(folder/'openroad.log').read_text()
config=b/'route-selection-102/sready181-full-cugr-inputs.json';assert not config.exists()
cfg=dict(schema='control162-openroad-search-snapshot-v1',iterations=1,nx=width//8000,ny=height//8000,inputs={n:dict(path=str(folder/n),sha256=sha(folder/n))for n in ['before.odb','route.guide','terminals.json','run.tcl']})
config.write_text(json.dumps(cfg,indent=2)+'\n')
state=json.loads((queue/'queue-state.json').read_text());assert len(state['active'])<=3
pending=queue/'pending/00-i-sready181-full-cugr-snapshot.json';out=b/'router-full-cugr-snapshot-181';assert not pending.exists()and not out.exists()
spec=dict(script='system_upper.py',source_root=str(source),forecast_gib=64,requires=[str(probe/'receipt.json')],args=list(map(str,['--manifest',base/'selected/physical.json','--graph',base/'topology/boundary-graph.json','--openroad-snapshot-config',config,'--out',out])))
temp=pending.with_suffix('.tmp');temp.write_text(json.dumps(spec));temp.rename(pending)
record.write_text(json.dumps(dict(time=time.time(),path=str(pending),sha256=sha(pending),config=str(config),config_sha256=sha(config),source_manifest_sha256=sha(source/'source-manifest.json'),original_scene=1513,original_net_count=len(terminals),reason='Bounded diagnostic replay of exact original1513 search ODB/global guides after actual12-net fixture replay passes original grid/flood/checkerboard with zero DRC. Emit actual DRC net pairs/locations and DEF after one optimization iteration to diagnose hundreds thousands shorts, rather than only repeat long searches. Original1513 and other full acceptance chains continue untouched; one own released16CPU slot, no additional node/cancellation. Diagnostic execution receipt cannot qualify a final system.'),indent=2)+'\n')
print('Queued actual8990-net diagnostic replay; original full search/physical gates untouched')
'''
compile(q,'actual_full_snapshot181','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
