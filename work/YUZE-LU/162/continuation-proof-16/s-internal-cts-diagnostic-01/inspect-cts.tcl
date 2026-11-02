set_thread_count 16
read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-internal-drive-02/candidate-1182/flow/results/nangate45/bv1_block_feed_s_macro/base/4_cts.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-internal-drive-02/candidate-1182/flow/results/nangate45/bv1_block_feed_s_macro/base/4_cts.sdc}
source {/OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl}
estimate_parasitics -placement
report_checks -path_delay max -group_path_count 16 -format full_clock_expanded -fields {slew cap fanout input net} -digits 6 > cts-setup.rpt
report_checks -path_delay min -group_path_count 8 -format full_clock_expanded -fields {slew cap fanout input net} -digits 6 > cts-hold.rpt
report_check_types -max_capacitance -max_slew -violators -digits 6 > cts-electrical.rpt
report_worst_slack -max
report_worst_slack -min
