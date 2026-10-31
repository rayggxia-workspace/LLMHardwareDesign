read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef}
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_verilog {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-806/tasks/revision300-load-v-base/load-map-fixture.v}
link_design revision300_load_map
create_clock -name core -period 3.333333333333 [get_ports clk]
set_load 72.6151662593587 [get_ports {q0}]
set_load 72.8582942282759 [get_ports {q1}]
write_sdc -no_timestamp -digits 12 {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-806/tasks/revision300-load-v-base/map-wrong-load.sdc}
