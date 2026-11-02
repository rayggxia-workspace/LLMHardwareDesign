# Actual propagated-clock path evidence chooses only failing external inputs.
set here [file dirname [file normalize [info script]]]
write_db $here/pre_input_hold.odb
write_sdc $here/pre_input_hold.sdc
set block [ord::get_db_block];set dbu [$block getDbUnitsPerMicron]
estimate_parasitics -placement
set worst [dict create];set internal 0;set external 0
foreach path [find_timing_paths -path_delay min -slack_max 0 -group_path_count 200000 -endpoint_path_count 1] {
 set start [get_property $path startpoint];set slack [get_property $path slack]
 if {![get_property $start is_port]} {incr internal;continue}
 incr external;set name [get_full_name $start]
 if {![dict exists $worst $name] || $slack<[dict get $worst $name]} {dict set worst $name $slack}
}
set f [open $here/INPUT_HOLD_AUDIT.tsv w]
puts $f "# failed_external_endpoints=$external failed_internal_endpoints=$internal unique_failing_inputs=[dict size $worst]"
set serial 0
# Front BUF_X16 stays close to the actual M10 pin; last BUF_X16 drives existing load tree.
dict for {name slack} $worst {
 if {$name eq "clk"} {error "clock used as data startpoint"}
 set term [$block findBTerm $name];if {$term eq "NULL"} {error "missing actual input"}
 set boxes {};foreach pin [$term getBPins] {foreach box [$pin getBoxes] {lappend boxes $box}}
 if {[llength $boxes]!=1} {error "nonunique input geometry"}
 set box [lindex $boxes 0];set location [list [expr {([$box xMin]+[$box xMax])/(2.0*$dbu)}] [expr {([$box yMin]+[$box yMax])/(2.0*$dbu)}]]
 set net [$term getNet]
 insert_buffer -buffer_cell BUF_X16 -net [$net getName] -location $location -buffer_name r166_input_front_$serial -net_name r166_input_front_wire_$serial
 set upstream [[$term getNet] getITerms];if {[llength $upstream]!=1} {error "unexpected split"}
 set front [[lindex $upstream 0] getInst];set chain [[$front findITerm Z] getNet]
 insert_buffer -buffer_cell BUF_X16 -net [$chain getName] -location $location -buffer_name r166_input_drive_$serial -net_name r166_input_drive_wire_$serial
 set load {}
 foreach term2 [$chain getITerms] {if {[[$term2 getMTerm] getIoType] eq "INPUT"} {lappend load $term2}}
 if {[llength $load]!=1} {error "unexpected chain input count"}
 set end [[lindex $load 0] getInst]
 set endpoint [get_pins [list "[$end getName]/A"]]
 set count [expr {int(ceil((0.060-$slack)/0.024))+2}]
 if {$count>64} {error "unexpected input delay requirement"}
 for {set i 0} {$i<$count} {incr i} {
  insert_buffer -buffer_cell CLKBUF_X1 -load_pins $endpoint -location $location -buffer_name r166_input_delay_${serial}_$i -net_name r166_input_delay_wire_${serial}_$i
 }
 puts $f "$name\t$slack\t$count\t[$front getName]\t[$end getName]"
 incr serial
}
close $f
if {$serial>0} {
 add_global_connection -net VDD -inst_pattern {r166_input_.*} -pin_pattern {VDD} -power
 add_global_connection -net VSS -inst_pattern {r166_input_.*} -pin_pattern {VSS} -ground
 global_connect
 set_dont_touch [get_cells r166_input_*]
 detailed_placement
 check_placement -verbose
 estimate_parasitics -placement
}
puts "R166_FAILING_INPUT_DELAY_PATHS=$serial;external_endpoints=$external;internal_endpoints=$internal"
write_db $here/post_input_hold.odb
write_sdc $here/post_input_hold.sdc
source $here/hold_endpoints.tcl
