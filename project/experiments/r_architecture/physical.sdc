set_cmd_units -time ns -capacitance fF -resistance kOhm -distance um
set_units -time ns -capacitance fF -resistance kOhm -distance um
create_clock -name core -period 3.33333333333 [get_ports clk]
set_clock_uncertainty 0.1 [get_clocks core]
set_clock_transition 0.05 [get_clocks core]
set data_inputs [remove_from_collection [all_inputs] [get_ports clk]]
set_input_delay -clock core -max 0.8 $data_inputs
set_input_delay -clock core -min 0.2 $data_inputs
set_output_delay -clock core -max 0.8 [all_outputs]
set_output_delay -clock core -min 0.2 [all_outputs]
set_driving_cell -lib_cell BUF_X2 -pin Z $data_inputs
set_load 50 [all_outputs]
