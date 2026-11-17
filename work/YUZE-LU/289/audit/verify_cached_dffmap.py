import json,sys,re,hashlib,collections
from pathlib import Path
p=Path(sys.argv[1]);top='e32_tiled_dot_loader'
a=json.loads((p/'before-dff.json').read_text())['modules'][top];b=json.loads((p/'after-dff.json').read_text())['modules'][top]
assert a['cells'].keys()==b['cells'].keys(),(len(a['cells']),len(b['cells']))
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
nff=0;ncomb=0
for name,x in a['cells'].items():
 y=b['cells'][name];assert x.get('parameters',{})==y.get('parameters',{})
 if x['type']=='$_DFF_P_':
  nff+=1;assert y['type']=='DFF_X1';pins={'C':'CK','D':'D','Q':'Q'}
  assert all(bit not in reads for bit in y['connections'].get('QN',[])),name
 else:
  ncomb+=1;assert x['type']==y['type'],(name,x['type'],y['type']);assert x['connections'].keys()==y['connections'].keys();pins={k:k for k in x['connections']}
 for k,v in pins.items():
  assert x['port_directions'][k]==y['port_directions'][v]
  expected=[t if isinstance(t,str) else fwd[t] for t in x['connections'][k]]
  assert expected==y['connections'][v],(name,k)
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
sys.path.insert(0,'/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/source/project/experiments/block_v1')
from native_cell_gate import group
body=group(lib.read_text(),'cell','DFF_X1');args=re.search(r'\bff\s*\(([^)]*)\)',body)[1];ff=group(body,'ff',args)
assert re.sub(r'[\s"]','',args)=='IQ,IQN'
assert re.findall(r'next_state\s*:\s*"([^"]+)"',ff)==['D']
assert re.findall(r'clocked_on\s*:\s*"([^"]+)"',ff)==['CK']
assert not re.search(r'\b(clear|preset|enable|clocked_on_also)\s*:',ff)
assert re.search(r'function\s*:\s*"IQ"',group(body,'pin','Q')) and re.search(r'function\s*:\s*"IQN"',group(body,'pin','QN'))
r={'passed':True,'flipflops':nff,'other_cells_exact':ncomb,'wire_bijection':len(fwd),'mapping':'all $_DFF_P_ C/D/Q -> DFF_X1 CK/D/Q exact connections; optional QN has no consumers; library rising-edge D-only FF semantics checked','hashes':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [p/'before-dff.json',p/'after-dff.json',lib]},'scope':'Strict DFF mapping stage in captured replay. Final actual-netlist binding is a separate receipt.'}
(p/'ff-mapping-receipt.json').write_text(json.dumps(r,indent=2));print(r)
