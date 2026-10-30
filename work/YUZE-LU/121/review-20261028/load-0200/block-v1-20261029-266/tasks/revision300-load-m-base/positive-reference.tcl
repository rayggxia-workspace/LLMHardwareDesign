read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef}
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-266/tasks/revision300-load-m-base/load-fixture.v}
link_design revision300_load_fixture
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-266/tasks/revision300-load-m-base/load-fixture.sdc}
set_load 45.5094789120992 [all_outputs]
write_sdc -no_timestamp -digits 12 {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-266/tasks/revision300-load-m-base/positive-reference.sdc}
