read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef}
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-806/tasks/revision300-boundary-rc-v-high/load-fixture.v}
link_design revision300_load_fixture
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-806/tasks/revision300-boundary-rc-v-high/load-fixture.sdc}
set_load 3 [all_outputs]
write_sdc -no_timestamp -digits 12 {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-806/tasks/revision300-boundary-rc-v-high/wrong-load-reference.sdc}
