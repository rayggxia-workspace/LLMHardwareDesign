from pathlib import Path
import sys,re,json,hashlib
p=Path(sys.argv[1]);mode=sys.argv[2];r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');run=r/'cu/runs/C-v24-joint-e20-h30'
h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
libs=re.search(r'^export ADDITIONAL_LIBS = (.*)$',(p/'model-run/config.mk').read_text(),re.M)[1].split()
files=[p/'gold.v',p/'gate.v',p/'model-run/config.mk',p/'c-formal.py',p/'c-control-packed-v3.py',p/'c-v24-proof-binding.py',run/'legalized.v',run/'config.mk']+[Path(x) for x in libs]
state={str(f):h(f) for f in files}
assert h(p/'gold.v')=='0d42fdd36b5c0ca3f9fc7682a34465dc6ef60732363be81b7eb465a87d7aa0c4'
assert h(p/'gate.v')==h(run/'legalized.v') and h(p/'model-run/config.mk')==h(run/'config.mk')
if mode=='before':(p/'input-binding.json').write_text(json.dumps(state,indent=2))
else:
 assert state==json.loads((p/'input-binding.json').read_text())
 receipts=[p/'formal/receipt.json',p/'controls-tag-v3-packed/receipt.json']
 assert all(json.loads(f.read_text())['passed'] for f in receipts)
 (p/'complete-equivalence-receipt.json').write_text(json.dumps(dict(passed=True,scope='Actual C-v16 synthesized design to frozen C-v24 e20/h30 legalized candidate data/state and clock/reset/enable controls, not physical signoff or a different candidate.',hashes=state,receipts={str(f):h(f) for f in receipts}),indent=2))
print(mode,'binding PASS')
