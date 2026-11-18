import hashlib,json,re,sys
from pathlib import Path
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu')
run=root/'runs/C-v24-joint-e20-h30'
files={run/'config.mk'}
for line in (run/'config.mk').read_text().splitlines():
 if re.match(r'export (ADDITIONAL_(LEFS|LIBS|GDS)|VERILOG_FILES|SDC_FILE) = ',line):
  files.update(Path(s) for s in line.split(' = ',1)[1].split() if s.startswith('/'))
for name in ['c-joint-edit-v2.tcl','c-joint-route-v1.tcl','c-joint-electric-v1.tcl','c-spacing-rip-v2.tcl','geometry.tcl','run-c-joint-v3.sh','c-joint-v4.sbatch','c-freeze-outputs-v1.tcl','c-dot-actual-cut-guard-v1.tcl','c-macro-access-ripup-v1.tcl','u-fresh-spef-pg.tcl']:
 files.add(root/name)
a={}
for p in sorted(files):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 a[str(p)]={'sha256':h.hexdigest(),'bytes':p.stat().st_size}
out=root/'diagnostics/C-joint-120013-source-manifest.json'
out.write_text(json.dumps({'accepted':False,'job':120013,'files':a},indent=2)+'\n')
print(str(out),len(a))
