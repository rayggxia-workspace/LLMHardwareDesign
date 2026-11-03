"""Independently extract immutable postroute data while original final LEC runs.

Diagnostic only. The original producer and every final gate still run normally.
Extraction commands mirror the exact frozen ORFS final_outputs.tcl sequence.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess

p=argparse.ArgumentParser();p.add_argument('--physical',type=Path,required=True);a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
S=a.physical;R=S/'flow/results/nangate45/r166_1024/base';platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
files=[R/('6_final.'+e)for e in ['odb','sdc','v']]+[platform/'rcx_patterns.rules',platform/'setRC.tcl',platform/'lib/NangateOpenCellLibrary_typical.lib',Path('/OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl')]
before={str(f):sha(f)for f in files};O=Path.cwd()/'postroute-rcx-probe';O.mkdir(exist_ok=False)
drt=json.loads((S/'flow/logs/nangate45/r166_1024/base/5_2_route.json').read_text());assert drt['detailedroute__route__drc_errors']==0
assert json.loads((S/'CLOCK_AUDIT_after-detail.json').read_text())['passed']
t='''set_thread_count 16
read_liberty {'''+str(platform/'lib/NangateOpenCellLibrary_typical.lib')+'''}
read_db {'''+str(R/'6_final.odb')+'''}
read_sdc {'''+str(R/'6_final.sdc')+'''}
source {'''+str(platform/'setRC.tcl')+'''}
define_process_corner -ext_model_index 0 X
set_extraction_rules_file {'''+str(platform/'rcx_patterns.rules')+'''}
extract_parasitics
write_spef probe.spef
read_spef probe.spef
set_propagated_clock [all_clocks]
sta::find_timing
set f [open timing-summary.tsv w]
puts $f "time_unit_seconds\t[sta::time_ui_sta 1]"
puts $f "setup_count\t[sta::endpoint_violation_count max]"
puts $f "hold_count\t[sta::endpoint_violation_count min]"
foreach kind {capacitance slew} {puts $f "$kind\t[sta::max_${kind}_violation_count]"}
close $f
set f [open failing-paths.tsv w]
foreach kind {min max} {
 foreach path [find_timing_paths -path_delay $kind -slack_max 0 -group_path_count 200000 -endpoint_path_count 1] {
  puts $f "$kind\t[get_full_name [get_property $path startpoint]]\t[get_full_name [get_property $path endpoint]]\t[get_property $path slack]"
 }
}
close $f
report_worst_slack -max -digits 9 > timing.rpt
report_worst_slack -min -digits 9 >> timing.rpt
report_checks -path_delay min_max -group_path_count 20 -digits 9 -format full_clock_expanded >> timing.rpt
'''
(O/'probe.tcl').write_text(t)
with(O/'probe.log').open('w')as log:r=subprocess.run(['openroad','-no_init','-exit','probe.tcl'],cwd=O,stdout=log,stderr=subprocess.STDOUT)
assert all(sha(Path(n))==h for n,h in before.items())
receipt=dict(passed=r.returncode==0,native_exit=r.returncode,physical=str(S),inputs=before,qualification=False,artifacts={f.name:dict(sha256=sha(f),bytes=f.stat().st_size)for f in O.iterdir()if f.is_file()},scope='Independent early extraction/STA diagnostic of exact immutable postroute ODB. Original final producer, LEC, final RCX/power, all physical/function gates and exact source binding still mandatory. No qualification or substitution of the final producer.')
(O/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');raise SystemExit(r.returncode)
