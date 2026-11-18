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
initialize_floorplan -utilization $::env(UTIL) -aspect_ratio 1 -core_space 10 -site FreePDK45_38x28
make_tracks
set_wire_rc -signal -layer metal3
set_wire_rc -clock -layer metal5
place_pins -hor_layers metal3 -ver_layers metal2
set_placement_padding -global -left 1 -right 1
global_placement -density [expr {$::env(UTIL)/100.0+0.1}] -skip_io
estimate_parasitics -placement
repair_design
repair_timing -setup
 detailed_placement
estimate_parasitics -placement
write_db placed.odb
write_verilog repaired.v
report_worst_slack -max -digits 6 > setup.rpt
report_checks -path_delay max -group_path_count 10 -format full_clock_expanded -fields {slew cap fanout} -digits 6 > paths.rpt
report_check_types -max_slew -max_capacitance -violators > electrical.rpt
report_design_area