read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $::env(CU_RESULTS)/4_1_pre_repair_setup_hold.odb
read_sdc $::env(CU_RESULTS)/4_1_pre_repair_setup_hold.sdc
set_propagated_clock [all_clocks]
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
estimate_parasitics -placement
report_checks -path_delay max -group_path_count 30 -format full_clock_expanded -fields {slew cap fanout} -digits 6 > $::env(CU_OUT)/setup-paths.rpt
report_checks -path_delay min -group_path_count 30 -format full_clock_expanded -digits 6 > $::env(CU_OUT)/hold-paths.rpt
report_worst_slack -max -digits 6 > $::env(CU_OUT)/setup.rpt
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 6 > $::env(CU_OUT)/electrical.rpt
