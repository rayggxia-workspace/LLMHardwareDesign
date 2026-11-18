set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set_thread_count 8
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db edited.odb
read_sdc $::env(CU_SEED)/4_1_pre_repair_setup_hold.sdc
set_propagated_clock [all_clocks]
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
source $root/pre-global-v3.tcl
estimate_parasitics -placement
report_checks -from [get_ports rst_ni] -path_delay min_max -format full_clock_expanded > reset-before.rpt
repair_timing -setup -setup_margin .030 -repair_tns 100 -verbose
source $root/pre-global-v3.tcl
estimate_parasitics -placement
report_checks -path_delay min_max -group_path_count 20 -format full_clock_expanded > repaired-paths.rpt
write_db setup-only.odb
write_sdc setup-only.sdc
write_verilog setup-only.v
source $root/geometry.tcl
geometry_snapshot geometry-repaired.tsv
sta::find_timing
puts "DIRECT_SETUP_ONLY_MIN_COUNT [sta::endpoint_violation_count min] MAX_COUNT [sta::endpoint_violation_count max]"
