"""Check physical-only buffer ownership on an immutable real global-route DB."""
from pathlib import Path
import argparse, hashlib, json, subprocess
p=argparse.ArgumentParser();p.add_argument('--odb',type=Path,required=True);a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
before=sha(a.odb);o=Path.cwd()/'locality-probe';o.mkdir(exist_ok=False)
hook=Path(__file__).parent/'buffer_locality.tcl'
# Put the audit beside this task's script, never in a frozen source directory.
(o/'buffer_locality.tcl').write_bytes(hook.read_bytes())
(o/'probe.tcl').write_text('''read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {%s}
write_verilog before.v
source buffer_locality.tcl
set first [r166_localize_buffers]
if {$first<=0} {error "No actual buffer ownership repaired"}
set second [r166_localize_buffers]
if {$second!=0} {error "Ownership is not idempotent"}
write_verilog after.v
puts "R166_LOCALITY_PROBE_PASS first=$first second=$second"
'''%str(a.odb))
with(o/'probe.log').open('w')as f:r=subprocess.run(['openroad','-no_init','-exit','probe.tcl'],cwd=o,stdout=f,stderr=subprocess.STDOUT)
unchanged=sha(a.odb)==before
same=(o/'after.v').is_file()and sha(o/'before.v')==sha(o/'after.v')
rec=dict(passed=r.returncode==0 and unchanged and same,input_odb=str(a.odb),input_sha256=before,source_odb_unchanged=unchanged,verilog_byte_identical=same,hook_sha256=sha(hook),scope='Physical ownership only; no placement/timing/DRC qualification')
(o/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');assert rec['passed']
