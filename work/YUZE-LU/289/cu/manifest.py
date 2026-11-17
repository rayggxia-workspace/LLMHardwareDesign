"""Read-only input evidence; execute on login node or allocated compute node."""
import hashlib,json,re,sys
from pathlib import Path
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu')
run=Path(sys.argv[1]).resolve()
assert root in run.parents
config=run/'config.mk'
paths={config,*root.glob('*.tcl'),*root.glob('*.sh'),*root.glob('*-outputs.txt')}
for line in config.read_text().splitlines():
    if '=' not in line:continue
    for word in line.split('=',1)[1].split():
        if word.startswith('/'):paths.add(Path(word))
for p in (run/'flow/results/nangate45').glob('*/base/4_cts.*'):paths.add(p)
rows=[]
for p in sorted(paths):
    if not p.is_file():continue
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    rows.append({'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()})
out=run/'inputs-manifest.json'
assert not out.exists(), 'Refusing to replace evidence'
out.write_text(json.dumps(rows,indent=2)+'\n')
print(out,len(rows))
