"""Queue exact small-regression replay, then16 original full search replays."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391';source=b/'source-199';record=b/'route-selection-102/sready200-complete-path-diagnostic';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert json.loads((source/'source-manifest.json').read_text())['commit']=='4d1d7c83f5c80c3dcc5079b34db306427e53b3d6'
kernel=b/'source-172/project/experiments/control_v1/tree_router.cpp';graph=c/'topology/boundary-graph.json';reg=b/'router-segment-regression-01/receipt.json';rd=json.loads(reg.read_text());assert rd['passed']and rd['inputs'][str(b/'source-145/project/experiments/control_v1/tree_router.cpp')]==sha(kernel)
original=c/'upper-candidates/1850/route';assert(original/'router').is_file()
for p in [source/'project/experiments/control_v1/router_conflict_snapshot.py',source/'project/experiments/control_v1/test_router_conflict_snapshot.py']:
 assert json.loads((source/'source-manifest.json').read_text())['files'][str(p.relative_to(source))]==sha(p)
record.mkdir();rows=[]
for kind in ['preflight','full']:
 cases=[]
 for i in range(3 if kind=='preflight'else 16):
  folder=(b/'router-segment-regression-01'/('case-%d-w1-lock0-negotiate0-defer0'%i))if kind=='preflight'else original/('trial-'+str(i))
  inp=folder/('router-input.txt'if kind=='preflight'else'input.txt');log=folder/'router.log';raw=log.read_bytes();snapshot=record/(kind+'-original-log-'+str(i)+'.txt');snapshot.write_bytes(raw)
  rounds=[json.loads(l)for l in raw.decode().splitlines()if l.startswith('{')and'"conflict_nodes"'in l];first=next(r for r in rounds if r['round']==0)
  cases.append(dict(case=i,input=str(inp),input_sha256=sha(inp),original_log_path=str(log),original_log_snapshot=str(snapshot),original_log_snapshot_sha256=sha(snapshot),expected_round0=first))
 config=record/(kind+'-config.json');config.write_text(json.dumps(dict(schema='control162-complete-path-snapshot-v1',kind=kind,kernel=str(kernel),graph=str(graph),sources=[dict(path=str(p),sha256=sha(p))for p in [kernel,graph,reg,original/'router',source/'project/experiments/control_v1/router_conflict_snapshot.py']],cases=cases),indent=2))
 out=b/('router-complete-path-'+kind+'-200');queue=b/'dynamic-04/node25';name='00-i-sready200-complete-path-preflight'if kind=='preflight'else'00-j-sready200-complete-path-full';path=queue/'pending'/(name+'.json');assert not path.exists()and not out.exists()
 deps=[reg]if kind=='preflight'else[b/'router-complete-path-preflight-200/receipt.json']
 spec=dict(script='router_conflict_snapshot.py',source_root=str(source),forecast_gib=32 if kind=='preflight'else 96,requires=list(map(str,deps)),args=list(map(str,['--config',config,'--out',out])))
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(path);rows.append(dict(path=str(path),sha256=sha(path),spec=spec,config=str(config),config_sha256=sha(config)))
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,source_manifest_sha256=sha(source/'source-manifest.json'),whole_system_qualified=False,scope='Three actual original regression cases, then16 actual original1850 one-round replays. Original source/kernel/inputs and original completed-round log snapshots bound. Every whole-path occupancy count must exactly repeat; original final gates unaffected. Existing own node25 slot only, original memory guard.'),indent=2))
print(json.dumps(dict(queued=len(rows),record=str(record),whole_system_qualified=False)))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
