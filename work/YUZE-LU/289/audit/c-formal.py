"""U parent ECO state-boundary equivalence across all actual macro pins."""
import sys,re,json,subprocess,hashlib
from pathlib import Path
runroot=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]).resolve(); out.mkdir(parents=True,exist_ok=True); proofdir=out/'formal';proofdir.mkdir()
res=next((runroot/'flow/results/nangate45').glob('*/*'))
gate=Path(sys.argv[4]).resolve()
root=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/source')
sys.path.insert(0,str(root/'project/experiments/block_v1'))
from native_logic_projection import project
from native_tie_projection import project as tie_project
from structural_view import compare
from native_formal import inspect
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
libs=re.search(r'^export ADDITIONAL_LIBS = (.*)$',(runroot/'config.mk').read_text(),re.M)[1].split()
top=re.search(r'^export DESIGN_NAME\s*=\s*(\S+)',(runroot/'config.mk').read_text(),re.M)[1]
macrotypes=set()
for path in libs:
 macrotypes.update(re.findall(r'\bcell\s*\(\s*"?([^"\s)]+)',Path(path).read_text()))
gold=Path(sys.argv[3]).resolve()
assert gold.exists() and gate.exists()
(out/'macrotypes.json').write_text(json.dumps(sorted(macrotypes)))

def run(args,name):
 with (proofdir/name).open('w') as f:subprocess.run(list(map(str,args)),cwd=proofdir,stdout=f,stderr=subprocess.STDOUT,check=True)
def yosys(name,script):
 p=proofdir/(name+'.ys');p.write_text(script);run(['yosys','-s',p],name+'.log')
boundaries=[]
for label,netlist in [('gold',gold),('gate',gate)]:
 source=''.join(f'read_liberty -lib {p}\n' for p in [lib]+libs)
 yosys(label+'-parse',source+f'read_verilog {netlist}\nhierarchy -check -top {top}\nwrite_json {label}-physical.json\n')
 data,passive=project(json.loads((proofdir/(label+'-physical.json')).read_text()),lib.read_text())
 data,ties=tie_project(data,lib.read_text());m=data['modules'][top]
 boundary=[]
 names=sorted(n for n,x in m['cells'].items() if x['type'] in macrotypes)
 assert names
 for i,name in enumerate(names):
  x=m['cells'].pop(name);assert not x['parameters']
  signature=[]
  for pin,direction in sorted(x['port_directions'].items()):
   assert direction in ('input','output')
   bits=x['connections'][pin];signature.append((pin,direction,len(bits)))
   key=f'__macro_{i}_{pin}';assert key not in m['ports'] and key not in m['netnames']
   m['ports'][key]=dict(direction='output' if direction=='input' else 'input',bits=bits[:])
   m['netnames'][key]=dict(hide_name=0,bits=bits[:],attributes={})
  boundary.append((name,x['type'],signature))
 boundaries.append(boundary)
 (proofdir/(label+'-cut.json')).write_text(json.dumps(data))
 (proofdir/(label+'-projection.json')).write_text(json.dumps(dict(passive=passive,ties=ties),indent=2))
 yosys(label+'-emit',f'read_json {label}-cut.json\nwrite_verilog -noattr -noexpr -norename {label}-cut.v\ndesign -reset\n'+source+f'read_verilog {label}-cut.v\nhierarchy -check -top {top}\nwrite_json {label}-readback.json\n')
 # Compare only the active top graph: macro blackboxes become unreferenced after the explicit cut.
 readback=json.loads((proofdir/(label+'-readback.json')).read_text())
 compare({'modules':{top:m}},{'modules':{top:readback['modules'][top]}})
assert boundaries[0]==boundaries[1]
cfg=proofdir/'kepler.yml';log=proofdir/'kepler.log'
cfg.write_text(f'format: verilog\ninput_paths:\n  - {proofdir}/gold-cut.v\n  - {proofdir}/gate-cut.v\nliberty_files:\n  - {lib}\nlog_file: {log}\n')
run(['/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal','--config',cfg],'command.log')
result=inspect(log.read_text());assert result['passed'],result
(proofdir/'receipt.json').write_text(json.dumps(dict(passed=True,proof=result,macro_boundary=boundaries[0],scope='C combinational/state-boundary correspondence including every macro input/output; state/control preservation remains separate',hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [gold,gate,lib]}),indent=2))
