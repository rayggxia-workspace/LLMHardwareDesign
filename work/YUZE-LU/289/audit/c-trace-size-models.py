from pathlib import Path
import re,json,sys,hashlib
sys.path.insert(0,'/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/source/project/experiments/block_v1')
from native_cell_gate import group,attribute
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib');text=lib.read_text();models={}
for name in re.findall(r'\bcell\s*\(\s*"?([^"\s)]+)',text):
 m=re.fullmatch(r'([A-Z0-9]+)_X(\d+)',name)
 if not m or name=='OAI221_X4':continue
 body=group(text,'cell',name)
 if re.search(r'\b(?:ff|ff_bank|latch|latch_bank|statetable)\s*\(',body):continue
 pins=[]
 for pin in re.findall(r'\bpin\s*\(\s*"?([^"\s)]+)',body):
  q=group(body,'pin',pin);direc=attribute(q,'direction');fn=attribute(q,'function',False);tri=attribute(q,'three_state',False)
  pins.append([pin,direc,re.sub(r'\s+','',fn) if fn else None,tri])
 if not any(x[1]=='output' and x[2] for x in pins):continue
 models[name]=dict(family=m[1],strength=int(m[2]),pins=sorted(pins),area=float(attribute(body,'area')))
config=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v27-joint-e20-h30/config.mk').read_text()
dont=set(' '.join(re.findall(r'^export DONT_USE_CELLS\s*=\s*(.*)$',config,re.M)).split())|{'OAI221_X4'}
covered=set()
for path in ['C-v28-cell-preflight','C-v29-cell-preflight']:
 covered.update(json.loads(Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/'+path+'/receipt.json').read_text())['masters'])
covered.add('AOI221_X4')
choices={}
for n,m in models.items():
 choices[n]=[v for v,t in sorted(models.items(),key=lambda x:x[1]['strength']) if t['family']==m['family'] and v!=n and t['pins']==m['pins'] and v in covered and v not in dont]
p=Path.cwd();(p/'models.json').write_text(json.dumps(dict(liberty=str(lib),liberty_sha256=hashlib.sha256(lib.read_bytes()).hexdigest(),models=models,choices=choices,dont_use=sorted(dont)),indent=2))
(p/'choices.tcl').write_text('set equivalents [dict create]\n'+''.join('dict set equivalents {%s} {%s}\n'%(n,' '.join(v)) for n,v in choices.items() if v))
