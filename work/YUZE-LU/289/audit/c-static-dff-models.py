from pathlib import Path
import re,json,sys,hashlib
sys.path.insert(0,'/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/source/project/experiments/block_v1')
from native_cell_gate import group,attribute
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib');text=lib.read_text();models={}
for name in ('DFF_X1','DFF_X2'):
 body=group(text,'cell',name);ff=re.search(r'\b(ff)\s*\(([^)]*)\)',body);assert ff
 assert not re.search(r'\b(?:ff_bank|latch|latch_bank|statetable|state_function)\s*[:(]',body)
 sig=[ff[1],re.sub(r'\s+','',ff[2]),re.sub(r'\s+','',group(body,ff[1],ff[2]))]
 pins=[]
 for pin in re.findall(r'\bpin\s*\(\s*"?([^"\s)]+)',body):
  q=group(body,'pin',pin);fn=attribute(q,'function',False)
  pins.append([pin,attribute(q,'direction'),re.sub(r'\s+','',fn) if fn else None,attribute(q,'three_state',False),attribute(q,'clock',False)])
 models[name]=dict(pins=sorted(pins),ff_signature=sig,area=float(attribute(body,'area')))
assert models['DFF_X1']['pins']==models['DFF_X2']['pins'] and models['DFF_X1']['ff_signature']==models['DFF_X2']['ff_signature']
p=Path.cwd();(p/'models.json').write_text(json.dumps(dict(liberty=str(lib),liberty_sha256=hashlib.sha256(lib.read_bytes()).hexdigest(),models=models,choices={'DFF_X1':['DFF_X2']},scope='Exact actual ff clocked_on/next_state/clear/preset/internal state labels plus every port direction/function/clock/three_state. No new state or initialization statement.'),indent=2));(p/'choices.tcl').write_text('set equivalents [dict create DFF_X1 {DFF_X2}]\n')
