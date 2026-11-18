import json,hashlib
from pathlib import Path
R=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');run=R/'cu/runs/C-v38-close-y640-h75'
expected={'legalized.v':'f7d43101ccb173e206388ef0314aaf2bd6831fb17537d30f761b47aa1b8ca41e','legalized.odb':'0d2951145ad943a7d05623d84a6423d807eabb49fbcbea8148e46f9cab223f71','config.mk':'faec62cb29a243a0e3147414f2248e8e05e87bfed6b64e254ee378ee1fd2c50f','inputs.sha256':'7de365e24a65f4af42b6cf2ce02f18f6eabfb0a3f7c95cbfb2e8a26fac7ada86'}
def h(f):return hashlib.sha256(f.read_bytes()).hexdigest()
for n,digest in expected.items():assert h(run/n)==digest,n
files=list(expected)+['edit-frozen.tcl','route-frozen.tcl','choices.txt','closure-hold-plan.tsv','longwire-placement.tcllist','placement-contract.tcllist','legalized.def']
fixtures=[str(R/'audit'/n/'receipt.json') for n in ['C-v28-cell-preflight','C-v29-cell-preflight','C-trace-AOI221X4-fixture','C-trace-additional-fixture']]
manifest=dict(gate=str(run/'legalized.v'),config=str(run/'config.mk'),odb=str(run/'legalized.odb'),provenance=str(run/'inputs.sha256'),expected_sha256={str(run/n):h(run/n) for n in files},fixture_receipts=fixtures)
out=R/'audit/C-v38-y640-h75-source-manifest.json';assert not out.exists();out.write_text(json.dumps(manifest,indent=2)+'\n');print(out)
