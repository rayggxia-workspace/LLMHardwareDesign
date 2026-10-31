set_thread_count 16
read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-322/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/3_5_place_dp.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-322/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/3_place.sdc}
source {/OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl}
estimate_parasitics -placement
sta::find_timing
report_worst_slack -max -digits 9 > paths.rpt
report_worst_slack -min -digits 9 >> paths.rpt
report_checks -path_delay min_max -group_path_count 12 -digits 9 -format full_clock_expanded >> paths.rpt
report_check_types -max_capacitance -max_slew -max_fanout -max_count 12 -digits 9 -no_line_splits > electrical.rpt
set f [open summary.tsv w]
puts $f "setup_violations\t[sta::endpoint_violation_count max]"
puts $f "hold_violations\t[sta::endpoint_violation_count min]"
close $f
