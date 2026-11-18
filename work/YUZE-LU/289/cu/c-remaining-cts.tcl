set_thread_count 2
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $::env(CU_SEED)/4_cts.odb
read_sdc $::env(CU_SEED)/4_cts.sdc
set_propagated_clock [all_clocks]
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
estimate_parasitics -placement
sta::find_timing
report_checks -path_delay min -group_path_count 1000 -slack_max 0 -format full_clock_expanded -digits 6 > $::env(CU_OUT)/remaining-hold.rpt
report_checks -path_delay max -group_path_count 1000 -slack_max 0 -format full_clock_expanded -digits 6 > $::env(CU_OUT)/remaining-setup.rpt
set f [open $::env(CU_OUT)/counts.tsv w]
foreach delay {min max} {puts $f "$delay\t[sta::endpoint_violation_count $delay]"}
close $f