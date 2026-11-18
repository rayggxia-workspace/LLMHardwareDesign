set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set run $root/u-macro-pdn-v1
read_db $root/runs/U-v6-ctsdelay-x8-seed0/flow/results/nangate45/u-overlay-current/base/4_cts.odb
source $root/rebase-evidence.tcl
rebase_evidence $run/before
pdngen -ripup
source /public/home/yuzelu/project-circuit/yzl-u-segment-softmax-250-20261116/physical/pdn.tcl
pdngen
rebase_evidence $run/after
write_db $run/pdn-candidate.odb
write_def $run/pdn-candidate.def
set f [open $run/pg-results.tsv w]
set failed 0
foreach rail {VDD VSS} {
 set code [catch {check_power_grid -net $rail} result]
 puts $f "$rail\t$code\t$result"
 if {$code || $result ne "1"} {set failed 1}
}
close $f
if {$failed} {error "Macro-specific PDN candidate not yet qualified"}
puts MACRO_SPECIFIC_PDN_CONNECTIVITY_PASSED
