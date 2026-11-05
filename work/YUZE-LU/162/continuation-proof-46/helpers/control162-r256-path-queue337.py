"""Queue source-bound legacy preflight and actual R256 full path replays."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-335';record=b/'route-selection-102/sready337-r256-complete-paths';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest=json.loads((source/'source-manifest.json').read_text());assert manifest['commit']=='e2c549e447c582bd676804ff44d9570831b855a6'
for n in ['router_conflict_snapshot.py','test_router_conflict_snapshot.py','r256_scene.py','system_upper.py']:
 p=source/'project/experiments/control_v1'/n;assert manifest['files'][str(p.relative_to(source))]==sha(p)
record.mkdir();rows=[];queue=b/'dynamic-03/node5'
for kind in ['preflight','full']:
 if kind=='preflight':
  old=b/'route-selection-102/sready200-complete-path-diagnostic/preflight-config.json';config=json.loads(old.read_text());config['sources'].append(dict(path=str(old),sha256=sha(old)))
  config['sources']=[r for r in config['sources']if not r['path'].endswith('/router_conflict_snapshot.py')]
 else:
  kernel=b/'source-305/project/experiments/control_v1/tree_router.cpp';graph=b/'r256-composition-274/topology/boundary-graph.json';original=b/'r256-composition-274/upper-candidates/2670/route';cases=[]
  for i in range(16):
   folder=original/('trial-'+str(i));inp=folder/'input.txt';log=folder/'router.log';raw=log.read_bytes();snapshot=record/('full-original-log-'+str(i)+'.txt');snapshot.write_bytes(raw)
   rounds=[json.loads(l)for l in raw.decode().splitlines()if l.startswith('{')and '"conflict_nodes"'in l];first=next(r for r in rounds if r['round']==0);assert first['conflict_nodes']>0
   cases.append(dict(case=i,input=str(inp),input_sha256=sha(inp),original_log_path=str(log),original_log_snapshot=str(snapshot),original_log_snapshot_sha256=sha(snapshot),expected_round0=first))
  config=dict(schema='control162-complete-path-snapshot-v1',kind=kind,kernel=str(kernel),graph=str(graph),sources=[dict(path=str(p),sha256=sha(p))for p in [kernel,graph,original/'router']],cases=cases)
 for p in [source/'project/experiments/control_v1/router_conflict_snapshot.py',source/'project/experiments/control_v1/r256_scene.py']:config['sources'].append(dict(path=str(p),sha256=sha(p)))
 cp=record/(kind+'-config.json');cp.write_text(json.dumps(config,indent=2)+'\n');out=b/('r256-complete-path-'+kind+'-337');name='00-a-sready337-path-'+('a-preflight'if kind=='preflight'else'b-full');path=queue/'pending'/(name+'.json');assert not path.exists()and not out.exists()
 deps=[]if kind=='preflight'else[b/'r256-complete-path-preflight-337/receipt.json']
 graph=Path(config['graph']);spec=dict(script='system_upper.py',source_root=str(source),forecast_gib=32 if kind=='preflight'else 96,requires=list(map(str,deps)),args=list(map(str,['--manifest',b/'r256-composition-274/configurations291.json','--graph',graph,'--router-conflict-snapshot-config',cp,'--out',out])))
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(path);rows.append(dict(path=str(path),sha256=sha(path),spec=spec,config=str(cp),config_sha256=sha(cp)))
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,source_manifest_sha256=sha(source/'source-manifest.json'),whole_system_qualified=False,scope='Exact original three-case preflight, then all16 actual2670 first-round complete search path replays for345 instances and11124 physical nets. Same original kernel/inputs/options, exact original round counts required. Diagnostic only. Existing own node5 4x16 dynamic queue and unchanged memory guard. No foreign jobs or original paths modified.'),indent=2)+'\n')
print(json.dumps(dict(queued=len(rows),record=str(record),whole_system_qualified=False)))
'''
compile(q,'queue337','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
