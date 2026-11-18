"""Remove declaration signedness from a purely structural mapped power view."""
from pathlib import Path
from hashlib import sha256
import json, re, subprocess

work=Path.cwd()
design=work.parent
source=design/'mapped.v'
dest=work/'mapped_sta.v'
before=sha256();after=sha256();count=0
pattern=re.compile(rb'^(\s*(?:wire|input|output|inout)) signed(\s)')
with source.open('rb') as src, dest.open('wb') as dst:
    for line in src:
        changed,n=pattern.subn(rb'\1\2',line)
        count+=n;before.update(line);after.update(changed);dst.write(changed)
assert count>0
synth=json.loads((design/'synth-receipt.json').read_bytes())
assert before.hexdigest()==synth['netlist_sha256']
platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
tcl=work/'check.tcl'
tcl.write_text('\n'.join([
    'read_liberty {'+str(platform/'lib/NangateOpenCellLibrary_typical.lib')+'}',
    'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.tech.lef')+'}',
    'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
    'read_verilog {'+str(dest)+'}', 'link_design block_v1_r',
    'puts "MAPPED_CELL_COUNT [llength [get_cells *]]"'])+'\n')
with (work/'check.log').open('w') as f:
    subprocess.run(['openroad','-no_init','-threads','4','-exit',str(tcl)],stdout=f,stderr=subprocess.STDOUT,check=True)
log=(work/'check.log').read_text()
cells=int(re.search(r'MAPPED_CELL_COUNT (\d+)',log)[1])
assert cells==synth['cell_count'],(cells,synth['cell_count'])
(work/'sta-view.json').write_text(json.dumps(dict(original_netlist_sha256=before.hexdigest(),
    sta_netlist_sha256=after.hexdigest(),removed_signed_declarations=count,cell_count=cells,
    transform='Only remove signed keyword on structural wire/port declarations. All names, widths, cells, pin connections and assign statements remain byte-identical.'),indent=2)+'\n')
print('STA_VIEW_PASS',cells,count,flush=True)
