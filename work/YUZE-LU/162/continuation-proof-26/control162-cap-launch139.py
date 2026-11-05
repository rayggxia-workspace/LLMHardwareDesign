import subprocess,shlex
q=r'''from pathlib import Path
import json,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-escape-composition-03/1350'
d=json.loads((c/'native-sta/native-system-audit.json').read_text())
def tiny(v):
 if isinstance(v,dict):return{k:(len(x)if isinstance(x,(list,dict))and len(x)>50 else tiny(x))for k,x in v.items()}
 if isinstance(v,list):return[tiny(x)for x in v[:8]]
 return v
print('Native typed timing passed:',d['typed']['passed'])
queue=b/'dynamic-05/node4/pending';index=b/'route-selection-102/s1350-cap-candidates1404-1407.json'
if index.exists():print('alreadyqueued');raise SystemExit(0)
rows=[]
for seed,gap in [(1404,64),(1405,256),(1406,64),(1407,256)]:
 out=c/'cap-candidates'/str(seed)
 args=['--manifest',str(c/'selected/physical.json'),'--graph',str(c/'topology/boundary-graph.json'),'--pg-wrappers',str(c/'fixed-pg-wrappers'),'--cap-lower-bound-only','--pin-aware-placement','--electrical-placement-report',str(c/'cap-preflight/wire-cap-lower-bound.json'),'--seed',str(seed),'--channel-gap-um',str(gap),'--out',str(out)]
 spec=dict(script='system_upper.py',source_root=str(b/'source-137'),forecast_gib=32,requires=[str(c/'cap-preflight/receipt.json')],args=args)
 name='00-k-s1350-electrical-cap-'+str(seed)+'.json';f=queue/name;assert not f.exists()and not out.exists();tmp=f.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(f);rows.append(dict(spec=str(f),out=str(out),seed=seed,gap=gap))
index.write_text(json.dumps(dict(tasks=rows,scope='Actual independent placement diagnostics; no geometry/RC acceptance inferred.'),indent=2));print('APPENDED',json.dumps(rows))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
