read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef}
read_lef {/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef}
read_verilog {/public/home/yuzelu/Melodydt/runs/issue-280/recurrent-round1-20261118/qwen35-fast/sta-view/mapped_sta.v}
link_design block_v1_r
create_clock -name core -period 5 [get_ports clk]
set_input_transition 0.05 [all_inputs]
read_vcd -scope calibrate_tb/dut {/public/home/yuzelu/Melodydt/runs/issue-280/recurrent-round1-20261118/full-pin-preflight/qwen35-fast/prefix.vcd}
report_activity_annotation
report_power -digits 9
