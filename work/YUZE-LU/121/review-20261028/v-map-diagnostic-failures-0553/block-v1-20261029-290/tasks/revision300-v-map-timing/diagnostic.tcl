read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-289/tasks/revision300-map-v/mapped.v}
link_design block_v1_v
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-290/tasks/revision300-v-map-timing/input.sdc}
report_checks -path_delay max -group_path_count 30 -format full_clock_expanded -fields {slew cap fanout input_pin net} -digits 9
report_worst_slack -max -digits 9
report_tns -digits 9
puts BV1_ZERO_WIRE_DIAGNOSTIC_COMPLETE
