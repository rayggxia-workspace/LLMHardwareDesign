set_thread_count 8
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $::env(CU_SOURCE_ODB)
read_sdc $::env(CU_SOURCE_SDC)
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
set_propagated_clock [all_clocks]
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/pre-global-v3.tcl
set_routing_layers -signal metal2-metal10 -clock metal2-metal10
set_global_routing_layer_adjustment metal2-metal10 $::env(CU_VALUE)
global_route -use_cugr -congestion_iterations 3 -verbose -congestion_report_file congestion.rpt
write_guides route.guide
write_db global-candidate.odb
estimate_parasitics -global_routing
report_worst_slack -min -digits 9 > estimated-hold.rpt
report_worst_slack -max -digits 9 > estimated-setup.rpt
puts CAPACITY_STUDY_ONLY_NOT_PHYSICAL_ACCEPTANCE