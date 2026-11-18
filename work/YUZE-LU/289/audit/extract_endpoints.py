import json,pathlib,collections
out=pathlib.Path(r'D:/Data/电路实验/LLMHardwareDesign-worktrees/ab-x8-20261117/work/YUZE-LU/289/audit')
arc=pathlib.Path(r'C:/Users/wine10/.codex/visualizations/2026/11/17/01a1e836-f66f-7262-8cfe-48c393b92969/routing-results-archive')
a=json.loads((out/'A-source-spec.json').read_text()); b=json.loads((arc/'B-four-links-pressure/spec.json').read_text()); ar=json.loads((arc/'A-qwen-two-links/original-route.json').read_text())
rows={}
for variant,spec in [('A',a),('B',b)]:
 for n in spec['nets']:
  if variant=='A' and n['id'] not in ar['routes']:continue
  eps=[n['driver']]+n['sinks']
  if any(p.split('.')[0].startswith('P') for p in eps):continue
  for sink in n['sinks']:
   key=(n['driver'],sink)
   r=rows.setdefault(key,dict(driver=key[0],sink=key[1],variants=[],net_ids={}))
   r['variants'].append(variant);r['net_ids'][variant]=n['id']
ports={}
for r in rows.values():
 for role in ['driver','sink']:
  ep=r[role]; owner,pin=ep.rsplit('.',1); dest=ports.setdefault(owner,dict(outputs=[],inputs=[]));target=dest['outputs' if role=='driver' else 'inputs']
  if pin not in target:target.append(pin)
result=dict(branches=list(rows.values()),ports=ports,counts=dict(branches=len(rows),by_variant={v:sum(v in r['variants'] for r in rows.values()) for v in ['A','B']}))
(out/'endpoints.json').write_text(json.dumps(result,indent=2)+'\n')
for owner,pins in ports.items():
 (out/(owner+'-outputs.txt')).write_text('\n'.join(pins['outputs'])+'\n')
 (out/(owner+'-inputs.txt')).write_text('\n'.join(pins['inputs'])+'\n')
print(result['counts']);print({k:{p:len(q) for p,q in v.items()} for k,v in ports.items()})
