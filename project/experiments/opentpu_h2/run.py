"""Read sealed H1 artifacts; create all new outputs in issue-31 only."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path.cwd()
SPEC = json.loads((ROOT/'spec.json').read_text())
SOURCE = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-15/top-split-reuse-20-01')
INPUTS = {}
def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()
def sealed(source,relative):
    manifest = {n[2:]:h for h,n in (line.split(None,1) for line in (source/'output.sha256').read_text().splitlines())}
    path = source/relative
    assert digest(path) == manifest[str(relative)], 'Changed sealed input '+str(path)
    INPUTS[str(path)] = digest(path)
    INPUTS[str(source/'output.sha256')] = digest(source/'output.sha256')
    return path
try:
    meta = json.loads(sealed(SOURCE,'experiment.json').read_text())
    odb = sealed(SOURCE,Path(meta['result_relative'])/'6_final.odb')
    args = dict(source=str(SOURCE),odb=str(odb),meta=meta)
    (ROOT/'inputs.json').write_text(json.dumps(args,indent=2)+'\n')
    with (ROOT/'physical-inventory.log').open('w') as log:
        subprocess.run(['openroad','-exit','-python',str(ROOT/'runner/physical.py')],stdout=log,stderr=subprocess.STDOUT,check=True)
finally:
    (ROOT/'input-sha256.json').write_text(json.dumps(INPUTS,indent=2)+'\n')
