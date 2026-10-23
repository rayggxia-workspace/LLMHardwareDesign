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
    script = 'read_db {'+str(odb)+'}\n'
    script += 'set b [ord::get_db_block]\nset f [open active-inventory.tsv w]\n'
    script += 'foreach i [$b getInsts] {puts $f "[$i getName]\\t[[$i getMaster] getName]\\t[$i getLocation]\\t[$i getOrient]\\t[$i getPlacementStatus]"}\nclose $f\n'
    script += 'set f [open connectivity.tsv w]\nforeach n [$b getNets] {foreach p [$n getITerms] {puts $f "[$n getName]\\t[$n getSigType]\\t[[$p getInst] getName]\\t[[$p getMTerm] getName]"}}\nclose $f\n'
    script += 'puts "WIRE_APIS [info commands odb::*Wire*]"\n'
    script += 'write_def physical.def\n'
    (ROOT/'physical.tcl').write_text(script)
    with (ROOT/'physical-inventory.log').open('w') as log:
        subprocess.run(['openroad','-threads',str(SPEC['cores']),'-exit',str(ROOT/'physical.tcl')],stdout=log,stderr=subprocess.STDOUT,check=True)
finally:
    (ROOT/'input-sha256.json').write_text(json.dumps(INPUTS,indent=2)+'\n')
