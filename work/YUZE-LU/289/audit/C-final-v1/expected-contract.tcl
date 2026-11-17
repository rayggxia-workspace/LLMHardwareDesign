# Canonical engineering contract, independently reconstructed on the exact candidate interface.
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(C_LIBS) {read_liberty $lib}
read_db $::env(C_FINAL_RES)/6_final.odb
create_clock -name clk -period 4 [get_ports clk_i]
set_clock_uncertainty 0.1 [get_clocks clk]
set_cmd_units -time ns -capacitance fF -resistance kOhm -distance um
set_clock_transition 0.05 [get_clocks clk]
set data_inputs [lsearch -all -inline -not -exact [all_inputs] [get_ports clk_i]]
set_input_delay -max 0.8 -clock clk $data_inputs
set_input_delay -min 0.2 -clock clk $data_inputs
set_driving_cell -lib_cell BUF_X2 -pin Z -input_transition_rise 0.05 -input_transition_fall 0.05 $data_inputs
set_output_delay -max 0.8 -clock clk [all_outputs]
set_output_delay -min 0.2 -clock clk [all_outputs]
set_load 2 [all_outputs]
set f [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/C-outputs.txt]
set count 0
while {[gets $f name]>=0} {
 if {$name eq ""} {continue}
 set p [get_ports [list $name]]
 if {[llength $p]!=1} {error "Selected output missing $name"}
 set_load 50 $p
 incr count
}
close $f
if {$count!=153} {error "Wrong selected output count"}
set_propagated_clock [all_clocks]
write_sdc -digits 9 expected-normalized.sdc
