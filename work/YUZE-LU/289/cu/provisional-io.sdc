# NEW engineering IO contract for the exact overlay logic, not historical acceptance.
# Reuses generic 250MHz block methodology from U segment route-input.sdc.
# No native_*/late_* overrides are transferred across incompatible interfaces.
# Apply after the preserved source clock/uncertainty SDC, baseline and X8 alike.
set_cmd_units -time ns -capacitance fF -resistance kOhm -distance um
set_clock_transition 0.05 [get_clocks clk]
set data_inputs [lsearch -all -inline -not -exact [all_inputs] [get_ports clk_i]]
set_input_delay -max 0.8 -clock clk $data_inputs
set_input_delay -min 0.2 -clock clk $data_inputs
set_driving_cell -lib_cell BUF_X2 -pin Z -input_transition_rise 0.05 -input_transition_fall 0.05 $data_inputs
set_output_delay -max 0.8 -clock clk [all_outputs]
set_output_delay -min 0.2 -clock clk [all_outputs]
set_load 2 [all_outputs]
