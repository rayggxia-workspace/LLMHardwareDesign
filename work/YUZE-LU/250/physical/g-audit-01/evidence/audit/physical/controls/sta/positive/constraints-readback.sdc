###############################################################################
# Created by write_sdc
# Wed Nov 11 01:01:43 2026
###############################################################################
current_design sta_probe
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name core -period 10.0000 [get_ports {clk}]
set_clock_transition 0.0500 [get_clocks {core}]
set_clock_uncertainty 0.1000 core
set_propagated_clock [get_clocks {core}]
set_input_delay 0.5000 -clock [get_clocks {core}] -min -add_delay [get_ports {d}]
set_input_delay 1.0000 -clock [get_clocks {core}] -max -add_delay [get_ports {d}]
set_output_delay 0.2000 -clock [get_clocks {core}] -min -add_delay [get_ports {q}]
set_output_delay 1.0000 -clock [get_clocks {core}] -max -add_delay [get_ports {q}]
###############################################################################
# Environment
###############################################################################
set_load -pin_load 2.0000 [get_ports {q}]
set_driving_cell -lib_cell BUF_X2 -pin {Z} -input_transition_rise 0.0000 -input_transition_fall 0.0000 [get_ports {d}]
###############################################################################
# Design Rules
###############################################################################
