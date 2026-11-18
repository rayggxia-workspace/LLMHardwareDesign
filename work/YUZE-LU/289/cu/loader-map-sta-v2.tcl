read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_verilog mapped.v
link_design e32_tiled_dot_loader
create_clock -name clk -period 4 [get_ports clk]
set_clock_uncertainty 0.1 [get_clocks clk]
set_clock_transition 0.05 [get_clocks clk]
set ins [lsearch -all -inline -not -exact [all_inputs] [get_ports clk]]
set_input_delay -max 0.8 -clock clk $ins
set_input_delay -min 0.2 -clock clk $ins
set_driving_cell -lib_cell BUF_X2 -pin Z -input_transition_rise 0.05 -input_transition_fall 0.05 $ins
set_output_delay -max 0.8 -clock clk [all_outputs]
set_output_delay -min 0.2 -clock clk [all_outputs]
set_load 2 [all_outputs]
report_worst_slack -max -digits 6 > setup.rpt
report_checks -from [all_registers -clock_pins] -to [all_registers -data_pins] -path_delay max -group_path_count 10 -format full_clock_expanded -digits 6 > reg2reg.rpt
report_design_area
