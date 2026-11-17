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
global_route -use_cugr -congestion_iterations 10 -verbose -congestion_report_file congestion.rpt
write_guides route.guide
write_db global-candidate.odb
estimate_parasitics -global_routing
report_worst_slack -min -digits 9 > estimated-hold.rpt
report_worst_slack -max -digits 9 > estimated-setup.rpt
sta::find_timing
set f [open estimated-counts.tsv w]
foreach delay {min max} {puts $f "$delay\t[sta::endpoint_violation_count $delay]"}
foreach kind {capacitance slew fanout} {puts $f "$kind\t[sta::max_${kind}_violation_count]"}
close $f
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 9 > estimated-electrical.rpt
report_checks -path_delay min_max -group_path_count 30 -format full_clock_expanded -digits 6 > estimated-paths.rpt
puts CAPACITY_STUDY_ONLY_NOT_PHYSICAL_ACCEPTANCE