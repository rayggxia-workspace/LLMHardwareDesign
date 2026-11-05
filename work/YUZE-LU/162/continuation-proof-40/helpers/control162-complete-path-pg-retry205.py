"""Preserve full203 failure; include both real PG nets and rerun original gates."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');base=b/'s-ready-composition-01/1391';source=b/'source-204';record=b/'route-selection-102/sready205-complete-path-with-PG';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert json.loads((source/'source-manifest.json').read_text())['commit']=='e8e5eabf38f33d6d641b904b1cee71768d774fd9'
prior=b/'router-complete-path-full-203/receipt.json';assert not json.loads(prior.read_text())['passed']
probe=b/'router-complete-path-preflight-203/receipt.json';assert json.loads(probe.read_text())['passed']
record.mkdir();rows=[]
for kind in ['preflight','full']:
 previous=b/'route-selection-102/sready203-complete-path-supported'/(kind+'-config.json');d=json.loads(previous.read_text());changes=[]
 for row in d['sources']:
  if'/source-202/'in row['path']:
   assert sha(row['path'])==row['sha256'];old=dict(row);row['path']=row['path'].replace('/source-202/','/source-204/');row['sha256']=sha(row['path']);changes.append(dict(previous=old,current=dict(row)))
 config=record/(kind+'-config.json');config.write_text(json.dumps(d,indent=2));out=b/('router-complete-path-'+kind+'-205');queue=b/'dynamic-04/node25';name='00-i-sready205-complete-path-preflight'if kind=='preflight'else'00-j-sready205-complete-path-full';p=queue/'pending'/(name+'.json');assert not out.exists()and not p.exists()
 deps=[probe]if kind=='preflight'else[b/'router-complete-path-preflight-205/receipt.json']
 spec=dict(script='system_upper.py',source_root=str(source),forecast_gib=32 if kind=='preflight'else 96,requires=list(map(str,deps)),args=list(map(str,['--manifest',base/'selected/physical.json','--graph',base/'topology/boundary-graph.json','--router-conflict-snapshot-config',config,'--out',out])))
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec,config=str(config),config_sha256=sha(config),source_changes=changes))
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,prior_failure=str(prior),prior_failure_sha256=sha(prior),prior_preflight=str(probe),prior_preflight_sha256=sha(probe),whole_system_qualified=False,scope='203 three original small cases replayed exactly, full diagnostic correctly rejected signal-only classification because actual routing has8988 signal plusVDD/VSS. Source204 explicitly includes both236-endpoint PG trees; do not drop nets or weaken exact whole8990-tree replay counts, flood, grid, via or wire budgets. Original all failed inputs/results preserved; no new cancellation/parent/R/foreign changes, same memory guard.'),indent=2))
print(json.dumps(dict(queued=len(rows),record=str(record),whole_system_qualified=False)))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
