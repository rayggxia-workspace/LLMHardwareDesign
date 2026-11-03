"""Test a no-op native incremental-routing bracket on an immutable final source.

References: OpenROAD src/grt/README.md (start/end_incremental) and LibreLane
usage/using_ecos.html (retain detailed routes during a finite buffer ECO).
This probe does not insert cells, change constraints, or confer qualification.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess

p=argparse.ArgumentParser();p.add_argument('--physical',type=Path,required=True);a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
S=a.physical;R=S/'flow/results/nangate45/r166_1024/base'
inputs={str(f):sha(f)for f in [R/'6_final.odb',R/'6_final.sdc',R/'route.guide',S/'receipt.json']}
assert json.loads((S/'receipt.json').read_text())['exit']==0
O=Path.cwd()/'incremental-route-probe';O.mkdir(exist_ok=False)
text='''set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {'''+str(R/'6_final.odb')+'''}
read_sdc {'''+str(R/'6_final.sdc')+'''}
write_def before.def
read_guides {'''+str(R/'route.guide')+'''}
global_route -start_incremental
global_route -end_incremental
write_def after.def
'''
(O/'probe.tcl').write_text(text)
with(O/'probe.log').open('w')as log:r=subprocess.run(['openroad','-no_init','-exit','probe.tcl'],cwd=O,stdout=log,stderr=subprocess.STDOUT)
identical=(O/'after.def').exists()and sha(O/'before.def')==sha(O/'after.def')
assert all(sha(Path(n))==h for n,h in inputs.items())
receipt=dict(passed=r.returncode==0 and identical,native_exit=r.returncode,physical=str(S),inputs=inputs,whole_native_def_bytes_identical=identical,qualification=False,artifacts={f.name:dict(sha256=sha(f),bytes=f.stat().st_size)for f in O.iterdir()if f.is_file()},scope='No-op incremental-routing capability/component probe only. Source never changed. No finite ECO, final extraction, full checks, or macro qualification inferred.',references=['https://openroad.readthedocs.io/en/latest/main/src/grt/README.html','https://librelane.readthedocs.io/en/stable/usage/using_ecos.html'])
(O/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items()if k not in ['artifacts','inputs']}))
raise SystemExit(0 if receipt['passed']else 1)
