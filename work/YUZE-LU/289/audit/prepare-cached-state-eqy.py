import json,subprocess,hashlib
from pathlib import Path
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit');v=p/'cached-eqy-stateviews';v.mkdir()
top='e32_tiled_dot_loader';ds=[];qs=[]
for lab in ('gold','gate'):
 src=p/'cached-eqy-v4'/(lab+'.il')
 ys=v/(lab+'.ys');ys.write_text(f'read_rtlil {src}\nwrite_json {v}/{lab}.json\n')
 with (v/(lab+'.log')).open('w') as log:subprocess.run(['yosys','-s',str(ys)],stdout=log,stderr=subprocess.STDOUT,check=True)
 d=json.loads((v/(lab+'.json')).read_text());m=d['modules'][top];ds.append(m)
 q={b for c in m['cells'].values() if c['type'].startswith(('$_DFF','$_SDFF','$_DLATCH','$dff','$adff','$sdff','$ff','$dffe')) for b in c['connections'].get('Q',[]) if isinstance(b,int)}
 assert q
 changed=True
 while changed:
  changed=False
  for c in m['cells'].values():
   if c['type'] in ('$not','$_NOT_','$buf','$_BUF_') and all(b in q for b in c['connections']['A']):
    for b in c['connections']['Y']:
     if isinstance(b,int) and b not in q:q.add(b);changed=True
 qs.append(q)
assert set(ds[0]['ports'])==set(ds[1]['ports'])
for n in ds[0]['ports']:assert ds[0]['ports'][n]['direction']==ds[1]['ports'][n]['direction'] and len(ds[0]['ports'][n]['bits'])==len(ds[1]['ports'][n]['bits'])
selected=sorted(ds[0]['ports']);covered=[{b for w in d['ports'].values() for b in w['bits'] if isinstance(b,int)} for d in ds]
internal=[]
for n,w in sorted(ds[0]['netnames'].items(),key=lambda kv:(-len(kv[1]['bits']),kv[0])):
 if n in selected or n.startswith(('_','$')) or '$' in n or n not in ds[1]['netnames']:continue
 arr=[w['bits'],ds[1]['netnames'][n]['bits']]
 if len(arr[0])!=len(arr[1]):continue
 ints=[{b for b in a if isinstance(b,int)} for a in arr]
 if not all(x and x<=q and not(x&seen) for x,q,seen in zip(ints,qs,covered)):continue
 internal.append(n)
 for seen,x in zip(covered,ints):seen.update(x)
selected+=internal
config=f'[gold]\nread_rtlil {p}/cached-eqy-v4/gold.il\n[gate]\nread_rtlil {p}/cached-eqy-v4/gate.il\n[match {top}]\n'
for n in selected:config+=f'final-gold-match {n}\n'
config+='gold-nomatch *\ngate-nomatch *\n[strategy simple]\nuse sat\ndepth 5\ntimeout 120\n'
(p/'cached-state-only.eqy').write_text(config)
(v/'selection.json').write_text(json.dumps({'ports_all_preserved':sorted(ds[0]['ports']),'state_aliases':internal,'excluded_wire_scope':'Only optional internal cutpoints; no ports, logic, states or assumptions removed. Each selected semantic state alias is driven by FF Q or inversion in both views; duplicated aliases avoided by actual bits.','input_sha':{lab:hashlib.sha256((p/'cached-eqy-v4'/(lab+'.il')).read_bytes()).hexdigest() for lab in ('gold','gate')}},indent=2))
print('MATCHED',len(selected),'ports',len(ds[0]['ports']),'state aliases',len(internal))
