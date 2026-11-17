from pathlib import Path
import hashlib,json
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');a=r/'u-physical/rcx-def-uncached-119788/normal';b=r/'u-physical/rcx-def-uncached-119810/original';dst=r/'audit/U-antenna/candidate-U-v17-postrcx';res=dst/'flow/results/nangate45/u-overlay-current/base'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def spef(p):
 lines=p.read_bytes().splitlines(keepends=True);dates=[x for x in lines if x.startswith(b'*DATE ')];assert len(dates)==1;return hashlib.sha256(b''.join(x for x in lines if not x.startswith(b'*DATE '))).hexdigest()
assert sha(a/'after.def')==sha(b/'after.def')==sha(res/'6_final.def')
assert sha(b/'after.odb')==sha(res/'6_final.odb')
assert sha(a/'isolated.spef')==sha(res/'6_final.spef')
assert spef(a/'isolated.spef')==spef(b/'isolated.spef')
files=[a/'after.def',b/'after.def',b/'after.odb',a/'isolated.spef',b/'isolated.spef',b/'run.log']+list(res.glob('6_final.*'))
v=dict(passed=True,scope='First normalized extraction repeated exactly: after DEF bytes identical; SPEF bytes identical except DATE header. Stage physical ODB from second repetition of first-pass input, GDS streamed from identical first-pass afterDEF.',spef_without_date_sha256=spef(a/'isolated.spef'),source_sha256={str(p):sha(p) for p in files},acceptance=False)
(dst/'first-pass-source-binding.json').write_text(json.dumps(v,indent=2))
