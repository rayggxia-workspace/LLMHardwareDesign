set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set_thread_count 8
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
set res $::env(CU_RESULTS)
read_db $res/4_cts.odb
read_sdc $res/4_cts.sdc
set_propagated_clock [all_clocks]
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
source $root/pre-global-v3.tcl
estimate_parasitics -placement
repair_timing -setup -setup_margin .030 -repair_tns 100 -verbose
detailed_placement
check_placement -verbose
estimate_parasitics -placement
sta::find_timing
set f [open setup-only-counts.tsv w]
foreach delay {min max} {puts $f "$delay\t[sta::endpoint_violation_count $delay]"}
close $f
report_worst_slack -min -digits 9 > setup-only-hold.rpt
report_worst_slack -max -digits 9 > setup-only-setup.rpt
report_checks -path_delay min_max -group_path_count 30 -format full_clock_expanded -digits 6 > setup-only-paths.rpt
write_db $res/4_setup_candidate.odb
write_sdc $res/4_setup_candidate.sdc
write_verilog $res/4_setup_candidate.v
geometry_snapshot geometry-setup-only.tsv
puts ACTUAL_SHARED_A_SETUP_DIAGNOSTIC_PENDING_HOLD_ROUTING_ELECTRICAL_AND_FULL_PHYSICAL