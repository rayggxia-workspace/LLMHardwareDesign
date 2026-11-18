import json,sys,re,hashlib,collections
from pathlib import Path
p=Path(sys.argv[1]);top='e32_tiled_dot_loader'
a=json.loads((p/'before-dff.json').read_text())['modules'][top];b=json.loads((p/'after-dff.json').read_text())['modules'][top]
assert set(a['cells'])<=set(b['cells'])
extra={n:b['cells'][n] for n in set(b['cells'])-set(a['cells'])}
assert all(c['type']=='$_MUX_' for c in extra.values())
fwd={};rev={}
def bind(x,y):
 if isinstance(x,str) or isinstance(y,str):assert x==y;return
 assert fwd.setdefault(x,y)==y and rev.setdefault(y,x)==x
for n,w in a['netnames'].items():
 assert n in b['netnames'];z=b['netnames'][n];assert len(w['bits'])==len(z['bits'])
 for x,y in zip(w['bits'],z['bits']):bind(x,y)
for n,w in a['ports'].items():
 z=b['ports'][n];assert w['direction']==z['direction'] and len(w['bits'])==len(z['bits'])
 for x,y in zip(w['bits'],z['bits']):bind(x,y)
reads={bit for c in b['cells'].values() for pin,bits in c['connections'].items() if c['port_directions'][pin]=='input' for bit in bits}|{bit for w in b['ports'].values() if w['direction']=='output' for bit in w['bits']}
extra_drivers={c['connections']['Y'][0]:(n,c) for n,c in extra.items()}
assert len(extra_drivers)==len(extra)
assert not set(extra_drivers)&set(fwd.values())
used_extra=set();nff=0;ncomb=0;tables=0;fftypes=collections.Counter()
def mapbit(t):return t if isinstance(t,str) else fwd[t]
def expression(bit,stack=()):
 if isinstance(bit,str):return bit
 if bit in rev:return rev[bit]
 assert bit in extra_drivers and bit not in stack
 n,c=extra_drivers[bit];used_extra.add(n)
 return ('mux',expression(c['connections']['A'][0],stack+(bit,)),expression(c['connections']['B'][0],stack+(bit,)),expression(c['connections']['S'][0],stack+(bit,)))
def variables(e):
 if isinstance(e,tuple):return set().union(*(variables(x) for x in e[1:]))
 return set() if e in ('0','1') else {e}
def value(e,v):
 if isinstance(e,tuple):return value(e[2] if value(e[3],v) else e[1],v)
 return int(e) if e in ('0','1') else v[e]
for name,x in a['cells'].items():
 y=b['cells'][name];assert x.get('parameters',{})==y.get('parameters',{})
 if 'FF' in x['type']:
  nff+=1;fftypes[x['type']]+=1
  assert y['type']=='DFF_X1'
  assert [mapbit(t) for t in x['connections']['C']]==y['connections']['CK']
  assert [mapbit(t) for t in x['connections']['Q']]==y['connections']['Q']
  assert all(bit not in reads for bit in y['connections'].get('QN',[])),name
  pin={k:v[0] for k,v in x['connections'].items()}
  assert all(len(v)==1 for v in x['connections'].values())
  assert sum(v in ('x','z') for v in pin.values())<=1
  D,Q=pin['D'],pin['Q'];typ=x['type']
  if typ=='$_DFF_P_':expected=D
  elif typ=='$_DFFE_PP_':expected=('mux',Q,D,pin['E'])
  elif typ=='$_SDFF_PP0_':expected=('mux',D,'0',pin['R'])
  elif typ=='$_SDFFE_PP0P_':expected=('mux',('mux',Q,D,pin['E']),'0',pin['R'])
  elif typ=='$_SDFFCE_PN0P_':expected=('mux',Q,('mux','0',D,pin['R']),pin['E'])
  else:raise AssertionError(typ)
  actual=expression(y['connections']['D'][0]);vars_=list(variables(expected)|variables(actual));assert len(vars_)<=5,(name,vars_)
  for k in range(1<<len(vars_)):
   v={n:(k>>i)&1 for i,n in enumerate(vars_)};assert value(expected,v)==value(actual,v),(name,typ,v,expected,actual);tables+=1
 else:
  ncomb+=1;assert x['type']==y['type'],(name,x['type'],y['type']);assert x['connections'].keys()==y['connections'].keys()
  for k,bits in x['connections'].items():assert [mapbit(t) for t in bits]==y['connections'][k],(name,k)
assert used_extra==set(extra)
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
sys.path.insert(0,'/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/source/project/experiments/block_v1')
from native_cell_gate import group
body=group(lib.read_text(),'cell','DFF_X1');args=re.search(r'\bff\s*\(([^)]*)\)',body)[1];ff=group(body,'ff',args)
assert re.sub(r'[\s"]','',args)=='IQ,IQN'
assert re.findall(r'next_state\s*:\s*"([^"]+)"',ff)==['D']
assert re.findall(r'clocked_on\s*:\s*"([^"]+)"',ff)==['CK']
assert not re.search(r'\b(clear|preset|enable|clocked_on_also)\s*:',ff)
assert re.search(r'function\s*:\s*"IQ"',group(body,'pin','Q')) and re.search(r'function\s*:\s*"IQN"',group(body,'pin','QN'))
r={'passed':True,'flipflops':nff,'other_cells_exact':ncomb,'wire_bijection':len(fwd),'mapping':'DFF/DFFE/SDFF/SDFFE/SDFFCE generic semantics exhaustively checked against actual new MUX cones and DFF_X1; all other cells/wires unchanged; optional QN unused','generic_types':dict(fftypes),'new_mux_cells':len(extra),'truth_table_assignments':tables,'hashes':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [p/'before-dff.json',p/'after-dff.json',lib]},'scope':'Strict DFF mapping stage in captured replay. Final actual-netlist binding is a separate receipt.'}
(p/'ff-mapping-receipt.json').write_text(json.dumps(r,indent=2));print(r)
