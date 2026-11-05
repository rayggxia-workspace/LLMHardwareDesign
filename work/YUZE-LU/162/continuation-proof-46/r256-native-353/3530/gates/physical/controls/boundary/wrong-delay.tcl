read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef}
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-native-353/3530/gates/physical/controls/boundary/fixture.v}
link_design revision300_boundary_fixture
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-native-353/3530/gates/physical/controls/boundary/wrong-delay-input.sdc}
write_sdc -no_timestamp -digits 12 {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-native-353/3530/gates/physical/controls/boundary/wrong-delay-readback.sdc}
