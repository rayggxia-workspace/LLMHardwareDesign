read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef}
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-286/tasks/revision300-boundary-rc-control/fixture.v}
link_design revision300_rc_fixture
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-286/tasks/revision300-boundary-rc-control/fixture.sdc}
read_spef {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-286/tasks/revision300-boundary-rc-control/structural/fixture.spef}
set_propagated_clock [all_clocks]
sta::find_timing
set f [open {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-286/tasks/revision300-boundary-rc-control/native-endpoints.tsv} w]
foreach pin [sta::endpoints] {puts $f "[get_full_name $pin]\t[get_property $pin slack_max]\t[get_property $pin slack_min]"}
close $f
report_parasitic_annotation -report_unannotated
report_checks -path_delay min_max -format full_clock_expanded -digits 12
