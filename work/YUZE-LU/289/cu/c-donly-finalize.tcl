set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set_thread_count 8
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db delayed.odb
read_sdc $::env(CU_SEED)/4_cts.sdc
set_propagated_clock [all_clocks]
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
detailed_placement
check_placement -verbose
estimate_parasitics -placement
report_checks -from [get_ports rst_ni] -path_delay min_max -format full_clock_expanded > reset-before.rpt
write_db legalized-before-setup.odb
repair_timing -setup -setup_margin .030 -repair_tns 100 -verbose
detailed_placement
check_placement -verbose
estimate_parasitics -placement
report_checks -path_delay min_max -group_path_count 20 -format full_clock_expanded > repaired-paths.rpt
write_db $::env(CU_RESULTS)/4_cts.odb
write_sdc $::env(CU_RESULTS)/4_cts.sdc
write_verilog $::env(CU_RESULTS)/4_cts.v
source $root/geometry.tcl
geometry_snapshot geometry-repaired.tsv