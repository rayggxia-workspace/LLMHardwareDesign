import sys,json,re,hashlib,subprocess,collections
from pathlib import Path
out=Path(sys.argv[1]).resolve(); f=out/'formal'; dest=out/'explicit-state-v2';dest.mkdir()
root=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/source/project/experiments/block_v1');sys.path.insert(0,str(root))
from native_cell_gate import group
from native_formal import inspect
from structural_view import compare
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib');text=lib.read_text();top='cfj_group_c_memory_legacy'
ds=[json.loads((f/(label+'-cut.json')).read_text()) for label in ('gold','gate')]
sem={}
for typ in {x['type'] for d in ds for x in d['modules'][top]['cells'].values()}:
 body=group(text,'cell',typ)
 if re.search(r'\b(?:ff|latch)\s*\(',body):
  ff=re.search(r'\b(ff|latch)\s*\(([^)]*)\)',body)
  assert ff[1]=='ff' and re.sub(r'\s+','',ff[2]).replace(chr(34),'')=='IQ,IQN'
  assert 'function' in group(body,'pin','Q') and re.search(r'function\s*:\s*"IQ"',group(body,'pin','Q'))
  assert re.search(r'function\s*:\s*"IQN"',group(body,'pin','QN'))
  sem[typ]=re.sub(r'\s+','',group(body,'ff',ff[2]))
 assert not re.search(r'\b(?:statetable|state_function)\b',body)
st=[{n:c for n,c in d['modules'][top]['cells'].items() if c['type'] in sem} for d in ds]
def aliases(d,states):
 m=d['modules'][top];aa=collections.defaultdict(set)
 for n,w in m['netnames'].items():
  for i,b in enumerate(w['bits']):
   if not w['hide_name']:aa[b].add((n,i))
 return {n:aa[c['connections']['Q'][0]] for n,c in states.items()}
al=[aliases(d,s) for d,s in zip(ds,st)]
pairs=[(n,n) for n in sorted(set(st[0])&set(st[1]))];used={b for a,b in pairs}
for n in sorted(set(st[0])-set(st[1])):
 candidates=[b for b in st[1] if b not in used and al[0][n]&al[1][b]]
 assert len(candidates)==1,(n,candidates)
 b=candidates[0];pairs.append((n,b));used.add(b)
extra=sorted(set(st[1])-used);assert len(pairs)==len(st[0])
for a,b in pairs:
 x,y=st[0][a],st[1][b]
 assert sem[x['type']]==sem[y['type']] and x['parameters']==y['parameters']
 assert x['port_directions']==y['port_directions']
 for attr in ('init','reset','preset'):assert x['attributes'].get(attr)==y['attributes'].get(attr)
# Net initialization must also agree for paired Q state; absent initialization is unconstrained.
initmaps=[]
for d in ds:
 im={}
 for w in d['modules'][top]['netnames'].values():
  if 'init' in w.get('attributes',{}):
   for bit,value in zip(w['bits'],w['attributes']['init'][::-1]):
    assert bit not in im or im[bit]==value;im[bit]=value
 initmaps.append(im)
for a,b in pairs:assert initmaps[0].get(st[0][a]['connections']['Q'][0])==initmaps[1].get(st[1][b]['connections']['Q'][0])
def port(m,key,direction,bits):
 assert key not in m['ports'];m['ports'][key]={'direction':direction,'bits':bits};m['netnames'][key]={'hide_name':0,'bits':bits,'attributes':{}}
def cut(m,n,key,observe):
 c=m['cells'].pop(n);q=c['connections']['Q'];qn=c['connections']['QN'];assert len(q)==len(qn)==1 and isinstance(q[0],int) and isinstance(qn[0],int)
 port(m,key+'_Q','input',q)
 inv=key+'_invert';assert inv not in m['cells']
 m['cells'][inv]={'hide_name':0,'type':'INV_X1','parameters':{},'attributes':{},'port_directions':{'A':'input','ZN':'output'},'connections':{'A':q,'ZN':qn}}
 if observe:
  for pin,direction in c['port_directions'].items():
   if direction=='input':port(m,key+'_'+pin,'output',c['connections'][pin])
for i,(a,b) in enumerate(pairs):
 for d,n in zip(ds,(a,b)):cut(d['modules'][top],n,f'__commonstate_{i}',True)
m=ds[0]['modules'][top];newbit=max(b for w in m['netnames'].values() for b in w['bits'] if isinstance(b,int))+1
for i,n in enumerate(extra):
 key=f'__extrastate_{i}';cut(ds[1]['modules'][top],n,key,False)
 m=ds[0]['modules'][top]
 port(m,key+'_Q','input',[newbit]);newbit+=1
for label,d in zip(('gold','gate'),ds):
 p=dest/(label+'.json');p.write_text(json.dumps(d))
 script=f'read_json {p}\nwrite_verilog -noattr -noexpr -norename {dest}/{label}.v\ndesign -reset\nread_liberty -lib {lib}\nread_verilog {dest}/{label}.v\nhierarchy -check -top {top}\nwrite_json {dest}/{label}-readback.json\n'
 ys=dest/(label+'.ys');ys.write_text(script)
 with (dest/(label+'.log')).open('w') as log:subprocess.run(['yosys','-s',str(ys)],stdout=log,stderr=subprocess.STDOUT,check=True)
 rb=json.loads((dest/(label+'-readback.json')).read_text());compare({'modules':{top:d['modules'][top]}},{'modules':{top:rb['modules'][top]}})
log=dest/'kepler.log';cfg=dest/'kepler.yml';cfg.write_text(f'format: verilog\ninput_paths:\n  - {dest}/gold.v\n  - {dest}/gate.v\nliberty_files:\n  - {lib}\nlog_file: {log}\n')
(dest/'mapping.json').write_text(json.dumps({'common_pairs':pairs,'extra_gate_states':extra,'scope':'universal arbitrary extra Q, common D and all clock/reset controls plus all top/macro outputs; QN=NOT Q per exact Liberty'},indent=2))
with (dest/'command.log').open('w') as o:subprocess.run(['/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal','--config',str(cfg)],stdout=o,stderr=subprocess.STDOUT,check=True)
r=inspect(log.read_text());assert r['passed'];(dest/'receipt.json').write_text(json.dumps({'passed':True,'proof':r,'common_states':len(pairs),'extra_gate_states':len(extra)},indent=2))
