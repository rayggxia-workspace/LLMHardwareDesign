import sys,json,re,hashlib,subprocess
from pathlib import Path
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit')
run=Path(sys.argv[1]).resolve();v=p/(run.name+'-live-state-generic-views');v.mkdir()
config=(run/'config.mk').read_text();top=re.search(r'^export DESIGN_NAME\s*=\s*(\S+)',config,re.M)[1]
libs=re.findall(r'^export ADDITIONAL_LIBS\s*=\s*(.*)$',config,re.M)[-1].split();types=set()
for f in libs:types.update(re.findall(r'\bcell\s*\(\s*"?([^"\s)]+)',Path(f).read_text()))
res=run/'flow/results/nangate45/c-overlay-current/base'
std='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
scripts={'gold':f'read_rtlil {res}/1_1_yosys_canonicalize.rtlil\nhierarchy -check -top {top}\nsynth -top {top} -flatten -noabc -extra-map /OpenROAD-flow-scripts/flow/platforms/common/lcu_kogge_stone.v\n', 'gate':f'read_json {p}/C-v21-A-synth-replay-isolated/abc/before-dff.json\n'}
ds=[];qs=[];boundaries=[]
for lab in ('gold','gate'):
 ys=v/(lab+'.ys');ys.write_text(scripts[lab]+f'write_json {v}/{lab}-uncut.json\n')
 with (v/(lab+'.log')).open('w') as log:subprocess.run(['yosys','-s',str(ys)],stdout=log,stderr=subprocess.STDOUT,check=True)
 d=json.loads((v/(lab+'-uncut.json')).read_text());m=d['modules'][top];boundary=[]
 for i,n in enumerate(sorted(n for n,c in m['cells'].items() if c['type'] in types)):
  c=m['cells'].pop(n);assert not c['parameters'];signature=[]
  for pin,direction in sorted(c['port_directions'].items()):
   assert direction in ('input','output');bits=c['connections'][pin];key=f'__macro_{i}_{pin}';assert key not in m['ports'] and key not in m['netnames']
   signature.append((pin,direction,len(bits)));m['ports'][key]={'direction':'output' if direction=='input' else 'input','bits':bits};m['netnames'][key]={'hide_name':0,'bits':bits,'attributes':{}}
  boundary.append((n,c['type'],signature))
 assert boundary;boundaries.append(boundary)
 assert all(c['type'].startswith('$') for c in m['cells'].values()),{c['type'] for c in m['cells'].values() if not c['type'].startswith('$')}
 (v/(lab+'.json')).write_text(json.dumps({'modules':{top:m}}));ds.append(m)
 q={b for c in m['cells'].values() if c['type'].startswith(('$_DFF','$_SDFF','$_DLATCH','$dff','$adff','$sdff','$ff','$dffe')) for b in c['connections'].get('Q',[]) if isinstance(b,int)}
 assert q;changed=True
 while changed:
  changed=False
  for c in m['cells'].values():
   if c['type'] in ('$not','$_NOT_','$buf','$_BUF_') and all(b in q for b in c['connections']['A']):
    for b in c['connections']['Y']:
     if isinstance(b,int) and b not in q:q.add(b);changed=True
 qs.append(q)
assert boundaries[0]==boundaries[1]
assert set(ds[0]['ports'])==set(ds[1]['ports'])
for n in ds[0]['ports']:assert ds[0]['ports'][n]['direction']==ds[1]['ports'][n]['direction'] and len(ds[0]['ports'][n]['bits'])==len(ds[1]['ports'][n]['bits'])
selected=sorted(ds[0]['ports']);covered=[{b for w in d['ports'].values() for b in w['bits'] if isinstance(b,int)} for d in ds];internal=[];aliasmap=[]
for n,w in sorted(list(ds[0]['netnames'].items()),key=lambda kv:(-len(kv[1]['bits']),kv[0])):
 if n in selected or n.startswith(('_','$')) or '$' in n or n not in ds[1]['netnames']:continue
 arr=[w['bits'],ds[1]['netnames'][n]['bits']]
 if len(arr[0])!=len(arr[1]):continue
 idx=[i for i in range(len(arr[0])) if all(isinstance(a[i],int) and a[i] in q and a[i] not in seen for a,q,seen in zip(arr,qs,covered))]
 if not idx:continue
 key='formal_live_state_'+str(len(internal));internal.append(key);aliasmap.append({'alias':key,'source':n,'indices':idx})
 for d,a,seen in zip(ds,arr,covered):
  assert key not in d['netnames'];bits=[a[i] for i in idx];d['netnames'][key]={'hide_name':0,'bits':bits,'attributes':{}};seen.update(bits)
selected+=internal
for label,m in zip(('gold','gate'),ds):(v/(label+'.json')).write_text(json.dumps({'modules':{top:m}}))
(v/'state-alias-map.json').write_text(json.dumps(aliasmap,indent=2))
s=f'[gold]\nread_json {v}/gold.json\n[gate]\nread_json {v}/gate.json\n[match {top}]\n'+''.join(f'final-gold-match {n}\n' for n in selected)
comboutputs=[n for n,v in ds[0]['ports'].items() if v['direction']=='output' and not all(isinstance(b,str) or b in qs[0] for b in v['bits'])]
s+=f'gold-nomatch *\ngate-nomatch *\n[collect {top}]\n'+''.join(f'bind {n}\n' for n in comboutputs)+'solo *\njoin *\n[strategy simple]\nuse sat\ndepth 5\ntimeout 60\n[strategy pdr]\nuse sby\nengine abc pdr\ntimeout 90\n'
assert any('cached_addr' in a['source'] for a in aliasmap)
(v/'proof.eqy').write_text(s)

(v/'binding.json').write_text(json.dumps({'all_ports':sorted(ds[0]['ports']),'state_aliases':internal,'macro_boundaries':boundaries[0],'source_hashes':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [res/'1_1_yosys_canonicalize.rtlil',res/'1_synth_lec.v',run/'config.mk',run/'loader-candidate.sv']},'scope':'All actual top and macro ports preserved; only optional proof matchpoints selected from FF Q/inversion aliases. No logic/state/port removal except explicit macro cut with all pins observed.'},indent=2))
print('PREPARED',v,'PORTS',len(ds[0]['ports']),'STATE_ALIASES',len(internal))
