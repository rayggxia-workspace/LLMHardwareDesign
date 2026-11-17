"""Independent ideal logic control-cone proof; physical clock/reset timing is a separate STA gate."""
import sys,json,re,hashlib,subprocess
from pathlib import Path
out=Path(sys.argv[1]).resolve(); f=out/'formal'; proofdir=out/'controls-tag-v2';proofdir.mkdir()
root=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/source/project/experiments/block_v1');sys.path.insert(0,str(root))
from native_cell_gate import group
from native_logic_projection import project
from native_tie_projection import project as ties
from native_formal import inspect
from structural_view import compare
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib');text=lib.read_text();top='cfj_group_c_memory_legacy'
macros=set(json.loads((out/'macrotypes.json').read_text()))
data=[json.loads((f/(label+'-physical.json')).read_text()) for label in ('gold','gate')]
controls={};semantics={}
for typ in {x['type'] for d in data for x in d['modules'][top]['cells'].values()}-macros:
 body=group(text,'cell',typ)
 assert not re.search(r'\b(?:statetable|state_function)\b',body),('unsupported sequential primitive',typ)
 if re.search(r'\b(?:ff|ff_bank|latch|latch_bank)\s*\(',body):
  expr=' '.join(re.findall(r'\b(?:clocked_on|clocked_on_also|enable|clear|preset)\s*:\s*"([^"]+)"',body))
  pins=set(re.findall(r'\bpin\s*\(\s*"?(\w+)"?\s*\)',body))
  ff=re.search(r'\b(ff|ff_bank|latch|latch_bank)\s*\(([^)]*)\)',body)
  semantics[typ]=(ff[1],re.sub(r'\s+','',ff[2]),re.sub(r'\s+','',group(body,ff[1],ff[2])))
  output_functions=sorted(re.findall(r'\bfunction\s*:\s*"([^"]+)"',body))
  semantics[typ]+=tuple(output_functions)
  controls[typ]=sorted(set(re.findall(r'[A-Za-z_]\w*',expr))&pins);assert controls[typ]
states=[{n:x for n,x in d['modules'][top]['cells'].items() if x['type'] in controls} for d in data]
assert set(states[0])==set(states[1]) and states[0]
for n,x in states[0].items():
 y=states[1][n];assert semantics[x['type']]==semantics[y['type']] and controls[x['type']]==controls[y['type']] and x['parameters']==y['parameters'],n
 attrs=lambda a:{k:v for k,v in a.items() if re.search('init|reset|preset',k,re.I)}
 assert attrs(x['attributes'])==attrs(y['attributes']),n
init=[{n:v['attributes']['init'] for n,v in d['modules'][top]['netnames'].items() if 'init' in v.get('attributes',{})} for d in data];assert init[0]==init[1]
def run(script,name):
 p=proofdir/(name+'.ys');p.write_text(script)
 with (proofdir/(name+'.log')).open('w') as log:subprocess.run(['yosys','-s',str(p)],cwd=proofdir,stdout=log,stderr=subprocess.STDOUT,check=True)
def tag_outputs(m):
 body=group(group(text,'cell','XOR2_X1'),'pin','Z')
 fn=re.search(r'function\s*:\s*"([^"]+)"',body)[1]
 assert re.sub(r'[\s()]','',fn)=='A^B'
 nxt=max(b for w in m['netnames'].values() for b in w['bits'] if isinstance(b,int))+1
 outputs=[(n,list(v['bits'])) for n,v in sorted(m['ports'].items()) if v['direction']=='output']
 for idx,(name,bits) in enumerate(outputs):
  observed=[]
  for k,bit in enumerate(bits):
   tag=f'__proof_tag_{idx}_{k}';cell=tag+'_xor'
   assert tag not in m['ports'] and tag not in m['netnames'] and cell not in m['cells']
   t,z=nxt,nxt+1;nxt+=2
   m['ports'][tag]={'direction':'input','bits':[t]};m['netnames'][tag]={'hide_name':0,'bits':[t],'attributes':{}}
   m['netnames'][cell+'_net']={'hide_name':0,'bits':[z],'attributes':{}}
   m['cells'][cell]={'hide_name':0,'type':'XOR2_X1','parameters':{},'attributes':{},'port_directions':{'A':'input','B':'input','Z':'output'},'connections':{'A':[bit],'B':[t],'Z':[z]}}
   observed.append(z)
  m['ports'][name]['bits']=observed;m['netnames'][name]={'hide_name':0,'bits':observed,'attributes':{}}

sigs=[]
for label,d in zip(('gold','gate'),data):
 d,_=project(d,text);d,_=ties(d,text);m=d['modules'][top]
 m['ports']={n:v for n,v in m['ports'].items() if v['direction']=='input'}
 names=sorted(n for n,x in m['cells'].items() if x['type'] in controls or x['type'] in macros)
 sig=[]
 for i,n in enumerate(names):
  x=m['cells'].pop(n);isstate=x['type'] in controls
  sig.append((n,semantics[x['type']] if isstate else x['type'],x['parameters'],sorted((p,v,len(x['connections'][p])) for p,v in x['port_directions'].items())))
  for pin,direction in sorted(x['port_directions'].items()):
   if direction=='output': direct='input'
   elif isstate and pin in controls[x['type']]:direct='output'
   else:continue
   key=f'__boundary_{i}_{pin}';assert key not in m['ports'];bits=x['connections'][pin]
   m['ports'][key]=dict(direction=direct,bits=bits[:]);m['netnames'][key]=dict(hide_name=0,bits=bits[:],attributes={})
 tag_outputs(m)
 sigs.append(sig);(proofdir/(label+'.json')).write_text(json.dumps(d))
 run(f'read_json {label}.json\nwrite_verilog -noattr -noexpr -norename {label}.v\ndesign -reset\nread_liberty -lib {lib}\nread_verilog {label}.v\nhierarchy -check -top {top}\nwrite_json {label}-readback.json\n',label)
 rd=json.loads((proofdir/(label+'-readback.json')).read_text());compare({'modules':{top:m}},{'modules':{top:rd['modules'][top]}})
assert sigs[0]==sigs[1]
cfg=proofdir/'kepler.yml';log=proofdir/'kepler.log';cfg.write_text(f'format: verilog\ninput_paths:\n  - {proofdir}/gold.v\n  - {proofdir}/gate.v\nliberty_files:\n  - {lib}\nlog_file: {log}\n')
with (proofdir/'command.log').open('w') as l:subprocess.run(['/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal','--config',str(cfg)],cwd=proofdir,stdout=l,stderr=subprocess.STDOUT,check=True)
r=inspect(log.read_text());assert r['passed'],r
(proofdir/'receipt.json').write_text(json.dumps(dict(passed=True,state_count=len(states[0]),controls=controls,state_semantics=semantics,drive_changes=[dict(instance=n,before=x['type'],after=states[1][n]['type']) for n,x in states[0].items() if x['type']!=states[1][n]['type']],proof=r,explicit_init=init[0],scope='All same-state CK/reset/enable cones Boolean-equivalent from same top inputs/state Q/macro outputs; no alias or identical-clock-tree assumption. Physical clock/reset propagation still requires full STA.',input_hashes={str(f/(n+'-physical.json')):hashlib.sha256((f/(n+'-physical.json')).read_bytes()).hexdigest() for n in ('gold','gate')}),indent=2))
