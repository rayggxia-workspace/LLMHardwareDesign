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
