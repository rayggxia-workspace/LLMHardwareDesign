read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef}
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-297/tasks/revision300-load-s-base/load-map-fixture.v}
link_design revision300_load_map
create_clock -name core -period 3.333333333333 [get_ports clk]
set_load 91.2620857931155 [get_ports {q0}]
set_load 91.5052137620327 [get_ports {q1}]
write_sdc -no_timestamp -digits 12 {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-297/tasks/revision300-load-s-base/map-wrong-load.sdc}
