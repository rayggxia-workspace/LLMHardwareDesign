###############################################################################
# Created by write_sdc
###############################################################################
current_design revision300_load_fixture
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name core -period 3.333333253860 [get_ports {clk}]
set_clock_transition 0.049999997020 [get_clocks {core}]
set_clock_uncertainty 0.099999994040 core
set_input_delay 0.199999988079 -clock [get_clocks {core}] -min -add_delay [get_ports {d}]
set_input_delay 0.799999952316 -clock [get_clocks {core}] -max -add_delay [get_ports {d}]
set_output_delay 0.199999988079 -clock [get_clocks {core}] -min -add_delay [get_ports {q}]
set_output_delay 0.799999952316 -clock [get_clocks {core}] -max -add_delay [get_ports {q}]
###############################################################################
# Environment
###############################################################################
set_load -pin_load 2.000000000000 [get_ports {q}]
set_driving_cell -lib_cell BUF_X2 -pin {Z} -input_transition_rise 0.000000000000 -input_transition_fall 0.000000000000 [get_ports {d}]
###############################################################################
# Design Rules
###############################################################################
