from pathlib import Path
import hashlib,json
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-upper-spacing-guard-v4')
assert 'C_SPACING_KEEPOUT_GEOMETRY_LOGIC_IDEMPOTENCE_PASS' in (p/'probe.log').read_text();assert (p/'before.v').read_bytes()==(p/'after.v').read_bytes();assert (p/'before-geometry.tsv').read_bytes()==(p/'after-geometry.tsv').read_bytes()
names=['hook.tcl','binding.tcl','keepout.tsv','master-geometry.tsv','ripup-nets.txt','receipt.json','derive.py','export.tcl','probe.tcl','probe.log','before-geometry.tsv','after-geometry.tsv']
v=dict(passed=True,accepted=False,probe_job=120001,scope='43 conservative localized spacing keepouts; pure master OBS append, idempotent, all die/pins/macro geometry and exported functional netlist exact. Not routing or full-deck qualification.',source_sha256={str(p/n):hashlib.sha256((p/n).read_bytes()).hexdigest() for n in names});(p/'frozen-manifest.json').write_text(json.dumps(v,indent=2));print(hashlib.sha256((p/'frozen-manifest.json').read_bytes()).hexdigest());print(v['source_sha256'][str(p/'hook.tcl')])
