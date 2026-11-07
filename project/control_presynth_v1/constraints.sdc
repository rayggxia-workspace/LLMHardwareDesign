# Single-clock control handoff budget. Ideal clock, pre-CTS, no path exceptions.
# Nangate45 typical uses ns and fF. set_units checks, rather than changes, units.
set_units -time ns -capacitance fF
create_clock -name control_clk -period 3.333333333 [get_ports clk_i]
set_clock_uncertainty -setup 0.05 [get_clocks control_clk]
set_clock_uncertainty -hold 0.02 [get_clocks control_clk]
set_clock_transition 0.05 [get_clocks control_clk]
set control_inputs [all_inputs -no_clocks]
set_input_delay -clock control_clk -max 0.5 $control_inputs
set_input_delay -clock control_clk -min 0.05 $control_inputs
set_input_transition 0.05 $control_inputs
set_output_delay -clock control_clk -max 0.5 [all_outputs]
set_output_delay -clock control_clk -min 0.05 [all_outputs]
set_load 5.0 [all_outputs]
# rst_ni is included in both input budgets. Do not suppress recovery/removal.
# Host is synchronous to clk_i; asynchronous hosts need a separate CDC contract.
