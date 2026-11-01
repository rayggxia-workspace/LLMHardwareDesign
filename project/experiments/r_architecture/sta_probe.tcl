set_thread_count 4
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef
read_verilog $::env(INPUT_NETLIST)
link_design $::env(INPUT_TOP)
read_sdc $::env(INPUT_SDC)
puts "METRICS_BEGIN"
report_worst_slack -max
report_worst_slack -min
report_design_area
report_checks -path_delay max -group_count 3 -fields {slew cap fanout input_pins net}
report_checks -path_delay min -group_count 1 -fields {slew cap fanout input_pins net}
report_check_types -max_capacitance -max_slew -max_fanout -violators
puts "METRICS_END"
set state_q {};set state_d {};set operand_d {}
foreach inst [[ord::get_db_block] getInsts] {
 if {![string match DFF* [[$inst getMaster] getName]]} {continue}
 set q [$inst findITerm Q];if {$q eq "NULL"} {continue};set net [$q getNet];if {$net eq "NULL"} {continue}
 set label [$net getName];set name [$inst getName]
 if {[regexp {^bank[01]\[} $label]} {lappend state_q ${name}/Q;lappend state_d ${name}/D}
 if {[regexp {^(operand_a|operand_b|operand_state_base|oa|ob|obase)\[} $label]} {lappend operand_d ${name}/D}
}
puts "CLASSIFIED_BANK_Q [llength $state_q] CLASSIFIED_BANK_D [llength $state_d] CLASSIFIED_OPERAND_D [llength $operand_d]"
puts "STATE_READ_PATH_BEGIN"
if {[llength $state_q]&&[llength $operand_d]} {report_checks -from [get_pins $state_q] -to [get_pins $operand_d] -path_delay max -group_count 1 -fields {slew cap fanout input_pins net}}
puts "STATE_READ_PATH_END"
puts "STATE_WRITE_PATH_BEGIN"
if {[llength $state_d]} {report_checks -to [get_pins $state_d] -path_delay max -group_count 1 -fields {slew cap fanout input_pins net}}
puts "STATE_WRITE_PATH_END"
