"""Append supported-entry retries; preserve rejected200 specs and receipts."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');base=b/'s-ready-composition-01/1391';source=b/'source-202';record=b/'route-selection-102/sready203-complete-path-supported';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert json.loads((source/'source-manifest.json').read_text())['commit']=='71c7150f71d24c0f5b71352e332bb7f409224492'
queue=b/'dynamic-04/node25';rejected=[]
for name in ['00-i-sready200-complete-path-preflight','00-j-sready200-complete-path-full']:
 p=queue/'results'/(name+'.json');d=json.loads(p.read_text());assert d['rejected_before_admission']and d['error']=='Unsupported task script';rejected.append(dict(path=str(p),sha256=sha(p),result=d))
record.mkdir();rows=[]
for kind in ['preflight','full']:
 original=b/'route-selection-102/sready200-complete-path-diagnostic'/(kind+'-config.json');d=json.loads(original.read_text())
 for row in d['sources']:
  if'/source-199/'in row['path']:row['path']=row['path'].replace('/source-199/','/source-202/');assert sha(row['path'])==row['sha256']
 module=source/'project/experiments/control_v1/system_upper.py';d['sources'].append(dict(path=str(module),sha256=sha(module)))
 config=record/(kind+'-config.json');config.write_text(json.dumps(d,indent=2));out=b/('router-complete-path-'+kind+'-203')
 name='00-i-sready203-complete-path-preflight'if kind=='preflight'else'00-j-sready203-complete-path-full';p=queue/'pending'/(name+'.json');assert not p.exists()and not out.exists()
 deps=[b/'router-segment-regression-01/receipt.json']if kind=='preflight'else[b/'router-complete-path-preflight-203/receipt.json']
 spec=dict(script='system_upper.py',source_root=str(source),forecast_gib=32 if kind=='preflight'else 96,requires=list(map(str,deps)),args=list(map(str,['--manifest',base/'selected/physical.json','--graph',base/'topology/boundary-graph.json','--router-conflict-snapshot-config',config,'--out',out])))
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec,config=str(config),config_sha256=sha(config)))
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,rejected_original=rejected,source_manifest_sha256=sha(source/'source-manifest.json'),whole_system_qualified=False,scope='Use existing supported system_upper entry. Original200 specs/results and source199 preserved. Three actual original small-case replays must pass before16 full original1850 one-round diagnostics. No scheduler whitelist/memory/final physical gate relaxation; existing free c96 slot only, no further cancellations.'),indent=2))
print(json.dumps(dict(queued=len(rows),record=str(record),whole_system_qualified=False)))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
