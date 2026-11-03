"""Queue balanced diagnostics into already free own16CPU slots; no cancellation."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');base=b/'s-ready-composition-01/1391';source=b/'source-197';record=b/'route-selection-102/sready197-balanced-local-placement.json';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert json.loads((source/'source-manifest.json').read_text())['commit']=='347e396de777e0393f190eef56ecb94ae5d01c59'
for old in [1960,1961]:
 p=base/'cap-capacity-candidates'/str(old)/'receipt.json';assert json.loads(p.read_text())['passed']
pin=base/'strong-local-native-pin-load-196/native-pin-load.json';prior=json.loads(pin.read_text());assert all(r['violations']['high']>0 for r in prior['placements']if Path(r['placement']).name in ['1960','1961'])
rows=[]
for node,seed,weight in [(3,1970,'1000000000'),(6,1971,'10000000000'),(3,1972,'0')]:
 queue=b/'dynamic-02'/('node'+str(node));dest=base/'cap-capacity-candidates'/str(seed);path=queue/'pending'/('00-j-sready197-balanced-local-'+str(seed)+'.json');assert not dest.exists()and not path.exists()
 args=['--manifest',base/'selected/physical.json','--graph',base/'topology/boundary-graph.json','--pg-wrappers',base/'fixed-pg-wrappers','--cap-lower-bound-only','--pin-aware-placement','--electrical-placement-report',base/'cap-initial/wire-cap-lower-bound.json','--placement-capacity-target','.35','--seed',(1580 if seed==1972 else seed),'--channel-gap-um',64,'--out',dest]
 if seed!=1972:args+=['--placement-residual-budget',base/'internal-channel-native-pin-load-158/native-pin-load.json','--placement-local-density-weight',weight]
 spec=dict(script='system_upper.py',source_root=str(source),forecast_gib=32,requires=[str(base/'cap-initial/receipt.json')],args=list(map(str,args)))
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(path);rows.append(dict(path=str(path),sha256=sha(path),spec=spec))
tmp=record.with_suffix('.tmp');tmp.write_text(json.dumps(dict(time=time.time(),tasks=rows,source_manifest_sha256=sha(source/'source-manifest.json'),prior_pin_bound_sha256=sha(pin),whole_system_qualified=False,scope='Only balanced search diagnostics in existing free own16CPU slots, same unchanged actual necessary and final gates, no cancellation or parent/R/other task changes.'),indent=2));tmp.rename(record)
print(json.dumps(dict(queued=len(rows),record=str(record),whole_system_qualified=False)))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
