import json,sys,re,hashlib,collections
from pathlib import Path
p=Path(sys.argv[1]);top='cfj_group_c_memory_legacy'
a=json.loads((p/'before-dff.json').read_text())['modules'][top];b=json.loads((p/'after-dff.json').read_text())['modules'][top]
assert set(a['cells'])<=set(b['cells'])
extra={n:b['cells'][n] for n in set(b['cells'])-set(a['cells'])}
assert all(c['type']=='$_MUX_' for c in extra.values())
fwd={};rev={}
def bind(x,y):
 if isinstance(x,str) or isinstance(y,str):assert x==y;return
 assert fwd.setdefault(x,y)==y and rev.setdefault(y,x)==x
for n,w in a['netnames'].items():
 assert n in b['netnames'];z=b['netnames'][n];assert len(w['bits'])==len(z['bits']);assert w.get('attributes',{}).get('init')==z.get('attributes',{}).get('init')
 for x,y in zip(w['bits'],z['bits']):bind(x,y)
for n,w in a['ports'].items():
 z=b['ports'][n];assert w['direction']==z['direction'] and len(w['bits'])==len(z['bits'])
 for x,y in zip(w['bits'],z['bits']):bind(x,y)
reads={bit for c in b['cells'].values() for pin,bits in c['connections'].items() if c.get('port_directions',{'CK':'input','D':'input','RN':'input','SN':'input','Q':'output','QN':'output'})[pin]=='input' for bit in bits}|{bit for w in b['ports'].values() if w['direction']=='output' for bit in w['bits']}
extra_drivers={c['connections']['Y'][0]:(n,c) for n,c in extra.items()}
assert len(extra_drivers)==len(extra)
assert not set(extra_drivers)&set(fwd.values())
used_extra=set();nff=0;ncomb=0;tables=0;fftypes=collections.Counter()
old_nots={c['connections']['Y'][0]:c['connections']['A'][0] for c in a['cells'].values() if c['type']=='$_NOT_'}
qn_roots={z:x['connections']['Q'][0] for n,x in a['cells'].items() if 'FF' in x['type'] for z in b['cells'][n]['connections'].get('QN',[])}
after_nots={c['connections']['Y'][0]:c['connections']['A'][0] for c in b['cells'].values() if c['type']=='$_NOT_'}
def negate(e):
 if e=='0':return '1'
 if e=='1':return '0'
 if isinstance(e,tuple) and e[0]=='not':return e[1]
 return ('not',e)
def norm_old(e,seen=()):
 if e in old_nots:
  assert e not in seen
  return negate(norm_old(old_nots[e],seen+(e,)))
 return e
for z in set(qn_roots)&set(rev):assert norm_old(rev[z])==negate(norm_old(qn_roots[z])),z
def mapbit(t):return t if isinstance(t,str) else fwd[t]
def expression(bit,stack=()):
 if isinstance(bit,str):return bit
 if bit in rev:return norm_old(rev[bit])
 if bit in qn_roots:return negate(norm_old(qn_roots[bit]))
 if bit in after_nots:
  assert bit not in stack
  return negate(expression(after_nots[bit],stack+(bit,)))
 assert bit in extra_drivers and bit not in stack
 n,c=extra_drivers[bit];used_extra.add(n)
 return ('mux',expression(c['connections']['A'][0],stack+(bit,)),expression(c['connections']['B'][0],stack+(bit,)),expression(c['connections']['S'][0],stack+(bit,)))
def variables(e):
 if isinstance(e,tuple):return set().union(*(variables(x) for x in e[1:]))
 return set() if e in ('0','1') else {e}
def value(e,v):
 if isinstance(e,tuple):
  if e[0]=='not':return 1-value(e[1],v)
  return value(e[2] if value(e[3],v) else e[1],v)
 return int(e) if e in ('0','1') else v[e]
for name,x in a['cells'].items():
 y=b['cells'][name];assert x.get('parameters',{})==y.get('parameters',{})
 if 'FF' in x['type']:
  nff+=1;fftypes[x['type']]+=1
  assert y['type'] in ('DFF_X1','DFFR_X1','DFFS_X1')
  assert [mapbit(t) for t in x['connections']['C']]==y['connections']['CK']
  assert [mapbit(t) for t in x['connections']['Q']]==y['connections']['Q']
  pin={k:v[0] for k,v in x['connections'].items()}
  assert all(len(v)==1 for v in x['connections'].values())
  assert sum(v in ('x','z') for v in pin.values())<=1
  pin={k:norm_old(v) for k,v in pin.items()}
  D,Q=pin['D'],pin['Q'];typ=x['type']
  m=re.fullmatch(r'\$_(S?DFF(?:CE|E)?)_([PN])([PN])?([01])?([PN])?_',typ);assert m,typ
  kind,clk,rpol,rval,epol=m.groups();assert clk=='P'
  async_reset=kind in ('DFF','DFFE') and rval is not None
  if kind=='DFFE' and rval is None:epol=rpol;rpol=None
  has_enable=kind.endswith('E')
  if has_enable:
   assert epol=='P',typ
  if async_reset:
   target='DFFR_X1' if rval=='0' else 'DFFS_X1';assert y['type']==target
   assert rpol=='N';rp='RN' if rval=='0' else 'SN'
   assert expression(y['connections'][rp][0])==pin['R']
  else:assert y['type']=='DFF_X1'
  expected=('mux',Q,D,pin['E']) if has_enable else D
  if kind.startswith('S'):
   assert rpol in ('P','N') and rval in ('0','1')
   reset_D=('mux',D,rval,pin['R']) if rpol=='P' else ('mux',rval,D,pin['R'])
   if kind=='SDFFCE':expected=('mux',Q,reset_D,pin['E'])
   else:expected=('mux',expected,rval,pin['R']) if rpol=='P' else ('mux',rval,expected,pin['R'])
  actual=expression(y['connections']['D'][0]);vars_=list(variables(expected)|variables(actual));assert len(vars_)<=5,(name,vars_)
  for k in range(1<<len(vars_)):
   v={n:(k>>i)&1 for i,n in enumerate(vars_)};assert value(expected,v)==value(actual,v),(name,typ,v,expected,actual);tables+=1
 else:
  ncomb+=1;assert x['type']==y['type'],(name,x['type'],y['type']);assert x['connections'].keys()==y['connections'].keys()
  for k,bits in x['connections'].items():
   if x['port_directions'][k]=='output' and x['type']!='$_NOT_':assert [mapbit(t) for t in bits]==y['connections'][k],(name,k)
   else:assert [norm_old(t) for t in bits]==[expression(t) for t in y['connections'][k]],(name,k)
assert used_extra==set(extra)
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
sys.path.insert(0,'/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/source/project/experiments/block_v1')
from native_cell_gate import group
for typ,reset,func in [('DFF_X1',None,None),('DFFR_X1','clear','!RN'),('DFFS_X1','preset','!SN')]:
 body=group(lib.read_text(),'cell',typ);args=re.search(r'\bff\s*\(([^)]*)\)',body)[1];ff=group(body,'ff',args)
 assert re.sub(r'[\s"]','',args)=='IQ,IQN'
 assert re.findall(r'next_state\s*:\s*"([^"]+)"',ff)==['D']
 assert re.findall(r'clocked_on\s*:\s*"([^"]+)"',ff)==['CK']
 for key in ['clear','preset','enable','clocked_on_also']:
  vals=re.findall(r'\b'+key+r'\s*:\s*"([^"]+)"',ff);assert vals==([func] if key==reset else []),(typ,key,vals)
 assert re.search(r'function\s*:\s*"IQ"',group(body,'pin','Q')) and re.search(r'function\s*:\s*"IQN"',group(body,'pin','QN'))
r={'passed':True,'flipflops':nff,'other_cells_exact':ncomb,'wire_bijection':len(fwd),'mapping':'DFF/DFFE/SDFF/SDFFE/SDFFCE generic semantics exhaustively checked against actual new MUX cones and DFF_X1; all other cells/wires unchanged; QN rewires checked against original inverter cones','generic_types':dict(fftypes),'new_mux_cells':len(extra),'truth_table_assignments':tables,'hashes':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [p/'before-dff.json',p/'after-dff.json',lib]},'scope':'Strict DFF mapping stage in captured replay. Final actual-netlist binding is a separate receipt.'}
(p/'ff-mapping-receipt.json').write_text(json.dumps(r,indent=2));print(r)
