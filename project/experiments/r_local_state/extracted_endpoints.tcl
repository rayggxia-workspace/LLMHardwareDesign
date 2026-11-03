# Finite, measured final-SPEF endpoint repair, not a positive-margin global sweep.
# All old placements stay fixed here; each new delay belongs to its actual host.
set originals {};set added {};set serial 0
foreach inst [$block getInsts] {
 lappend originals [list [$inst getName] [$inst getPlacementStatus] [$inst getLocation] [$inst getOrient]]
 $inst setPlacementStatus LOCKED
}
set out [open $here/EXTRACTED_ENDPOINT_ECO.tsv w]
puts $out "endpoint\tbuffer\tmaster\tgroup\tx_dbu\ty_dbu"
dict for {name count} $r166_endpoint_delays {
 set slash [string last / $name];set inst [$block findInst [string range $name 0 [expr {$slash-1}]]]
 if {$inst eq "NULL" || [string range $name [expr {$slash+1}] end] ne "D" || ![string match DFF* [[$inst getMaster] getName]]} {error "Measured data endpoint no longer exists: $name"}
 set pin [get_pins [list $name]]
 if {[llength $pin]!=1} {error "Nonunique data endpoint $name"}
 lassign [$inst getLocation] x y;set location [list [expr {$x/double($dbu)}] [expr {$y/double($dbu)}]]
 set owner [$inst getGroup]
 for {set i 0} {$i<$count} {incr i} {
  if {$serial>=5000} {error "Measured endpoint ECO exceeded finite cell guard"}
  set bn [format "r166_hold_endpoint_extracted_%05d" $serial]
  insert_buffer -buffer_cell CLKBUF_X1 -load_pins $pin -location $location -buffer_name $bn -net_name ${bn}_wire
  set drivers {};foreach term [[[$inst findITerm D] getNet] getITerms] {if {[[$term getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $term}}
  if {[llength $drivers]!=1} {error "Measured endpoint split not unique $name"}
  set new [[lindex $drivers 0] getInst]
  if {![string match "$bn*" [$new getName]] || [[$new getMaster] getName] ne "CLKBUF_X1"} {error "Unexpected inserted endpoint driver"}
  if {$owner ne "NULL"} {
   set region [$block findRegion [string range [$owner getName] 0 end-6]]
   if {$region eq "NULL"} {error "Endpoint host region missing"}
   $region addInst $new;$owner addInst $new
   $new setLocation $x $y;$new setPlacementStatus PLACED
  } else {r166_host_input $new $location}
  lappend added [list $name [$new getName]];incr serial
 }
}
add_global_connection -net VDD -inst_pattern {r166_hold_endpoint_extracted_.*} -pin_pattern {VDD} -power
add_global_connection -net VSS -inst_pattern {r166_hold_endpoint_extracted_.*} -pin_pattern {VSS} -ground
global_connect
set_dont_touch [get_cells r166_hold_endpoint_extracted_*]
detailed_placement -max_displacement {50 10}
check_placement -verbose
foreach row $originals {
 lassign $row name status location orient;set inst [$block findInst $name]
 if {[$inst getLocation] ne $location || [$inst getOrient] ne $orient} {error "Unrelated placement moved during measured endpoint repair"}
 $inst setPlacementStatus $status
}
foreach row $added {
 lassign $row endpoint name;set inst [$block findInst $name]
 foreach pg {VDD VSS} {set pin [$inst findITerm $pg];if {$pin eq "NULL" || [$pin getNet] eq "NULL" || [[$pin getNet] getName] ne $pg} {error "Unconnected endpoint delay supply"}}
 set group [$inst getGroup];set groupname none;if {$group ne "NULL"} {set groupname [$group getName]}
 lassign [$inst getLocation] x y
 puts $out "$endpoint\t$name\t[[$inst getMaster] getName]\t$groupname\t$x\t$y"
 $inst setPlacementStatus LOCKED
}
close $out
puts "R166_EXTRACTED_ENDPOINT_ECO=[dict size $r166_endpoint_delays]; cells=$serial; old_placements_unchanged=1; original_final_gates_required=1"
