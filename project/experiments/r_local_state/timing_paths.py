"""Read-only extracted path localization before a measured timing ECO."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess
p=argparse.ArgumentParser();p.add_argument('--physical',type=Path,required=True);p.add_argument('--capacity',type=int,required=True);p.add_argument('--hold-selection-ns',type=float,default=0);a=p.parse_args();assert 0<=a.hold_selection_ns<=0.020
R=a.physical/'flow/results/nangate45'/('r166_'+str(a.capacity))/'base'
O=Path.cwd()/'path-diagnosis';O.mkdir(exist_ok=False)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
files=[R/('6_final.'+ext)for ext in ['odb','sdc','spef']];before={str(f):sha(f)for f in files}
t='''set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {%s}
read_sdc {%s}
read_spef {%s}
set_propagated_clock [all_clocks]
sta::find_timing
set f [open failing-paths.tsv w]
foreach kind {min max} {
 set cutoff [expr {$kind eq "min" ? %s : 0}]
 foreach path [find_timing_paths -path_delay $kind -slack_max $cutoff -group_path_count 200000 -endpoint_path_count 1] {
  puts $f "$kind\t[get_full_name [get_property $path startpoint]]\t[get_full_name [get_property $path endpoint]]\t[get_property $path slack]"
 }
}
close $f
report_checks -path_delay min_max -group_path_count 20 -digits 9 -format full_clock_expanded > paths.rpt
'''%tuple([str(f)for f in files]+[str(a.hold_selection_ns)])
(O/'probe.tcl').write_text(t)
with(O/'probe.log').open('w')as log:r=subprocess.run(['openroad','-exit','probe.tcl'],cwd=O,stdout=log,stderr=subprocess.STDOUT)
assert before=={f:sha(Path(f))for f in before}
(O/'receipt.json').write_text(json.dumps(dict(passed=r.returncode==0,inputs=before,hold_selection_threshold_ns=a.hold_selection_ns,script_sha256=sha(O/'probe.tcl'),scope='Read-only actual extracted negative and explicitly selected near-critical hold paths. Selection threshold is a repair-planning input, never a changed acceptance gate; no qualification.'),indent=2)+'\n')
raise SystemExit(r.returncode)
