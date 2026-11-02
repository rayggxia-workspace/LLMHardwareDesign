# Native OpenROAD ECO: protect actual loaded data inputs with local buffers.
# Existing pins, logic, clock tree, layer rules and acceptance SDC stay fixed.
set here [file dirname [file normalize [info script]]]
source $here/required_ports.tcl
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
remove_fillers
set original {}
foreach inst [$block getInsts] {
 lappend original [list [$inst getName] [$inst getPlacementStatus] [$inst getLocation] [$inst getOrient]]
 $inst setPlacementStatus LOCKED
}
set removed 0
foreach net [$block getNets] {
 if {[$net getSigType] in {POWER GROUND}} {continue}
 set wire [$net getWire]
 if {$wire ne "NULL"} {odb::dbWire_destroy $wire;incr removed}
}
set audit [open $here/PORT_BUFFER_AUDIT.tsv w]
puts $audit "port\tbuffer\told_loads\tpin_x_um\tpin_y_um\tfinal_x_um\tfinal_y_um"
set buffers {};set covered {};set index 0
foreach term [$block getBTerms] {
 if {[$term getIoType] ne "INPUT" || [$term getName] eq "clk"} {continue}
 if {[$term getSigType] in {POWER GROUND CLOCK}} {continue}
 set net [$term getNet];set loads [llength [$net getITerms]]
 if {$loads==0} {continue}
 set name [$term getName];set boxes {}
 foreach pin [$term getBPins] {
  foreach box [$pin getBoxes] {if {[[$box getTechLayer] getName] eq "metal10"} {lappend boxes $box}}
 }
 if {[llength $boxes]!=1} {error "expected exactly one metal10 input pin: $name"}
 set box [lindex $boxes 0]
 set x [expr {([$box xMin]+[$box xMax])/(2.0*$dbu)}]
 set y [expr {([$box yMin]+[$box yMax])/(2.0*$dbu)}]
 set buffer [format "r157_io_%04d" $index];set newnet [format "r157_io_wire_%04d" $index]
 insert_buffer -buffer_cell BUF_X16 -net [$net getName] -location [list $x $y] -buffer_name $buffer -net_name $newnet
 # This tool version appends a global unique counter to the requested base.
 # Identify and validate the actual instance through the protected port net.
 set upstream [[$term getNet] getITerms]
 if {[llength $upstream]!=1} {error "native input split has multiple upstream loads: $name"}
 set a [lindex $upstream 0];set inst [$a getInst]
 if {![string match "$buffer*" [$inst getName]] || [[$inst getMaster] getName] ne "BUF_X16" || [[$a getMTerm] getName] ne "A"} {error "unexpected native input buffer $name"}
 set buffer [$inst getName];set z [$inst findITerm Z]
 if {[$a getNet] ne [$term getNet] || [llength [[$a getNet] getITerms]]!=1 || [llength [[$z getNet] getITerms]]!=($loads+1)} {error "input split mismatch $name"}
 set master [$inst getMaster]
 $inst setLocation [expr {round($x*$dbu-[$master getWidth]/2.0)}] [expr {round($y*$dbu-[$master getHeight]/2.0)}]
 $inst setPlacementStatus PLACED
 set_dont_touch [get_cells $buffer]
 lappend buffers [list $name $buffer $loads $x $y];lappend covered $name
 incr index
}
foreach name $r157_required_ports {if {$name ni $covered} {error "unprotected audited input $name"}}
if {$index==0} {error "no input buffers inserted"}
add_global_connection -net VDD -inst_pattern {r157_io_.*} -pin_pattern {VDD} -power
add_global_connection -net VSS -inst_pattern {r157_io_.*} -pin_pattern {VSS} -ground
global_connect
detailed_placement -max_displacement {10 10}
check_placement -verbose
foreach row $original {
 lassign $row name status location orient
 set inst [$block findInst $name]
 if {[$inst getLocation] ne $location || [$inst getOrient] ne $orient} {error "existing placement moved: $name"}
 $inst setPlacementStatus $status
}
foreach row $buffers {
 lassign $row name buffer loads x y
 set inst [$block findInst $buffer];lassign [$inst getLocation] fx fy
 $inst setPlacementStatus LOCKED
 puts $audit "$name\t$buffer\t$loads\t$x\t$y\t[expr {$fx/double($dbu)}]\t[expr {$fy/double($dbu)}]"
}
close $audit
puts "R157_IO_BUFFER_INSERTED=$index; removed_regular_wires=$removed; required=[llength $r157_required_ports]; original_placement_unchanged=1"
