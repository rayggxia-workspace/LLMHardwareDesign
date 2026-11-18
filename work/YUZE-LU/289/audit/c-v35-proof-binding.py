from pathlib import Path
import sys,re,json,hashlib
p=Path(sys.argv[1]);mode=sys.argv[2];r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');run=r/'cu/runs/C-v35-unified-i8-h100-pmid200'
h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
libs=re.search(r'^export ADDITIONAL_LIBS = (.*)$',(p/'model-run/config.mk').read_text(),re.M)[1].split()
files=[p/'gold.v',p/'gate.v',p/'model-run/config.mk',p/'c-formal.py',p/'c-control-packed-v3.py',p/'c-v35-proof-binding.py',run/'legalized.v',run/'config.mk']+[Path(x) for x in libs]
dep=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/source/project/experiments/block_v1')
files += [dep/(x+'.py') for x in ['native_logic_projection','native_tie_projection','structural_view','native_formal','native_cell_gate']]
files += [run/n for n in ['inputs.sha256','physical-choice.txt','prep-frozen.tcl','edit-frozen.tcl','route-frozen.tcl','legalized.odb']]
state={str(f):h(f) for f in files}
assert h(p/'gate.v')=='298be06b704c783d3a31902fbc41b4033ce842600470af7b818e17a371b9a9c2'
assert h(run/'legalized.odb')=='c76b40ae1a2dcede5a271369ef85f62c56145e794e7e3d59997c25adaa25a320'
assert h(run/'config.mk')=='faec62cb29a243a0e3147414f2248e8e05e87bfed6b64e254ee378ee1fd2c50f'
assert h(run/'inputs.sha256')=='90bc6790d98ac96f498d4f75a53966c2a8d6142fcbf9f7ff56c80e081881fc64'
assert h(p/'gold.v')=='0d42fdd36b5c0ca3f9fc7682a34465dc6ef60732363be81b7eb465a87d7aa0c4'
assert h(p/'gate.v')==h(run/'legalized.v') and h(p/'model-run/config.mk')==h(run/'config.mk')
if mode=='before':(p/'input-binding.json').write_text(json.dumps(state,indent=2))
else:
 assert state==json.loads((p/'input-binding.json').read_text())
 receipts=[p/'formal/receipt.json',p/'controls-tag-v3-packed/receipt.json']
 assert all(json.loads(f.read_text())['passed'] for f in receipts)
 (p/'complete-equivalence-receipt.json').write_text(json.dumps(dict(passed=True,scope='Actual C-v16 synthesized design to frozen C-v35 i8/h100/pmid200 legalized candidate data/state and clock/reset/enable controls, not physical signoff or a different candidate.',hashes=state,receipts={str(f):h(f) for f in receipts}),indent=2))
print(mode,'binding PASS')
