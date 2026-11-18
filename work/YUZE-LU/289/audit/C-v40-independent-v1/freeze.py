"""Freeze audit inputs only after CU explicitly confirms a complete candidate.

Usage: python3 freeze.py RUN OUTPUT_DIRECTORY 'CU freeze confirmation and choice'
No EDA submission, copying of large artifacts, or backend acceptance occurs here.
"""
from pathlib import Path
import hashlib,json,re,sys
run=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();confirmation=sys.argv[3].strip()
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
assert run.parent==root/'cu/runs' and re.fullmatch(r'C-v40-final-size-seed[0-5]',run.name)
assert confirmation, 'Explicit completed-file freeze confirmation required'
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def manifest(path):
 rows={}
 for line in path.read_text().splitlines():
  h,name=line.split(maxsplit=1);f=Path(name);f=f if f.is_absolute() else path.parent/f;f=f.resolve();assert re.fullmatch('[a-f0-9]{64}',h)
  assert sha(f)==h, ('Producer manifest mismatch',str(f));rows[str(f)]=h
 return rows
res=run/'flow/results/nangate45/c-overlay-current/base'
required=[res/('6_final.'+ext) for ext in ('odb','def','gds','spef','sdc','v')]+[res/('6_post_rcx.'+ext) for ext in ('odb','def')]
required += [run/n for n in ('candidate.sha256','inputs.sha256','status.txt','route-status.txt','config.mk','route-frozen.tcl','choices.txt','fresh-counts.tsv','fresh-pg-after-spef.tsv','fresh-setup.rpt','fresh-hold.rpt','gds.log','fresh.log')]
for f in required:assert f.is_file() and f.stat().st_size>0, ('Incomplete candidate',str(f))
producer=manifest(run/'candidate.sha256');inputs=manifest(run/'inputs.sha256')
common=root/'cu/runs/C-v40-final-sizes'
inputs.update(manifest(common/'prepared.sha256'));inputs.update(manifest(common/'inputs.sha256'))
required += [common/n for n in ('prepared.sha256','inputs.sha256','edit-frozen.tcl','route-frozen.tcl','size-plan.tsv','config.mk')]
assert all(str(res/('6_final.'+ext)) in producer for ext in ('odb','def','gds','spef','sdc','v'))
assert 'accepted=false_pending_all_final_gates' in (run/'status.txt').read_text()
config=(run/'config.mk').read_text();views={}
for name in ('ADDITIONAL_LIBS','ADDITIONAL_LEFS','ADDITIONAL_GDS','VERILOG_FILES'):
 values=re.findall(r'^export '+name+r'\s*=\s*(.*)$',config,re.M);assert values,name
 for value in values[-1].split():
  f=Path(value);assert f.is_absolute() and f.is_file();views[str(f)]=sha(f)
helpers=[root/'cu'/n for n in ('geometry.tcl','c-freeze-outputs-v1.tcl','u-fresh-spef-pg.tcl','run-c-final-route-seed-v1.sh','C-outputs.txt')]
helpers += [root/'cu/diagnostics/C-v28-i8-h50/original-signatures.tcllist']
helpers += [root/'audit/C-final-v1'/n for n in ('geometry-all.tcl','def-material.py','antenna-meta.tcl','antenna-map.py','final-evidence.tcl','expected-contract.tcl','check.py','inputs.py')]
helpers += [root/'u-physical/upper-spacing-diagnostic-v2.lydrc',root/'audit/U-antenna/antenna-only-v2.lydrc']
baseline=Path('/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/C/flow/results/nangate45/c-overlay-current/base/4_cts.odb')
hashes=dict(inputs,**views);hashes.update({str(f):sha(f) for f in required+helpers+[baseline]})
counts=dict(line.split('\t') for line in (run/'fresh-counts.tsv').read_text().splitlines());assert set(counts)=={'max','min','capacitance','slew','fanout'}
counts={k:int(v) for k,v in counts.items()}
code={str(f):sha(f) for f in Path(__file__).resolve().parent.iterdir() if f.is_file()}
assert hashes=={name:sha(Path(name)) for name in hashes}, 'Source changed while binding'
out.mkdir(parents=True,exist_ok=False)
data=dict(accepted=False,source_frozen_for_independent_audit=True,confirmation=confirmation,run=str(run),results=str(res),original_geometry_odb=str(baseline),producer_fresh_counts=counts,files_sha256=hashes,audit_code_sha256=code,scope='Same-candidate binding only; no previous nine-net, antenna, timing or native-marker pass is inherited.')
(out/'frozen-source.json').write_text(json.dumps(data,indent=2));print(json.dumps(dict(output=str(out),counts=counts),indent=2))
