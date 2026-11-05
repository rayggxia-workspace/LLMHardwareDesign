set p /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $p/lib/NangateOpenCellLibrary_typical.lib
read_liberty /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib
read_db $::env(ODB)
read_sdc /public/home/yuzelu/project-circuit/LLMHardwareDesign/local-s-sram-qualification-20261105-01/attempt02/n4/physical/input.sdc
report_checks -path_delay max -group_path_count 20 -unique_paths_to_endpoint -format full_clock_expanded -fields {slew cap fanout net} -digits 4
report_worst_slack -max
