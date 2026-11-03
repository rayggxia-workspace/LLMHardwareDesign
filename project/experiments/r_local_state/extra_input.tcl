# Shared input delay selected only by exact final SPEF failing paths.
set originals {}
foreach inst [$block getInsts] {
 lappend originals [list [$inst getName] [$inst getPlacementStatus] [$inst getLocation] [$inst getOrient]]
 $inst setPlacementStatus LOCKED
}
set audit [open $here/EXTRACTED_INPUT_ECO.tsv w];set serial 0
dict for {name slack} $r166_extra_ports {
 set term [$block findBTerm $name]
 set root [[$term getNet] getITerms]
 if {[llength $root]!=1} {error "nonunique protected input $name"}
 set front [[lindex $root 0] getInst]
 if {![string match r166_io_* [$front getName]] || [[$front getMaster] getName] ne "BUF_X16"} {error "no short-pin protection"}
 lassign [$front getLocation] x y;set location [list [expr {$x/double($dbu)}] [expr {$y/double($dbu)}]]
 set net [[$front findITerm Z] getNet]
 unset_dont_touch [get_cells [list [$front getName]]]
 $front setPlacementStatus PLACED
 insert_buffer -buffer_cell BUF_X16 -net [$net getName] -location $location -buffer_name r166_extra_drive_$serial -net_name r166_extra_drive_wire_$serial
 $front setPlacementStatus LOCKED
 set_dont_touch [get_cells [list [$front getName]]]
 set load {};foreach iterm [$net getITerms] {if {[[$iterm getMTerm] getIoType] eq "INPUT"} {lappend load $iterm}}
 if {[llength $load]!=1} {error "extra drive split failed"}
 set drive [[lindex $load 0] getInst];set endpoint [get_pins [list "[$drive getName]/A"]]
 set count [expr {int(ceil((0.040-$slack)/0.024))}]
 for {set i 0} {$i<$count} {incr i} {
  insert_buffer -buffer_cell CLKBUF_X1 -load_pins $endpoint -location $location -buffer_name r166_extra_delay_${serial}_$i -net_name r166_extra_wire_${serial}_$i
 }
 puts $audit "$name\t$slack\t$count\t[$front getName]\t[$drive getName]"
 incr serial
}
close $audit
set added {}
foreach inst [$block getInsts] {
 if {![string match r166_extra_* [$inst getName]]} {continue}
 lappend added $inst;lassign [$inst getLocation] x y
 foreach region [$block getRegions] {
  foreach box [$region getBoundaries] {
   if {$x>=[$box xMin] && $x<[$box xMax] && $y>=[$box yMin] && $y<[$box yMax]} {
    $region addInst $inst;[$block findGroup "[$region getName]_cells"] addInst $inst
   }
  }
 }
}
add_global_connection -net VDD -inst_pattern {r166_extra_.*} -pin_pattern {VDD} -power
add_global_connection -net VSS -inst_pattern {r166_extra_.*} -pin_pattern {VSS} -ground
global_connect
set_dont_touch [get_cells r166_extra_*]
detailed_placement -max_displacement {10 10}
check_placement -verbose
foreach row $originals {
 lassign $row name status location orient;set inst [$block findInst $name]
 if {[$inst getLocation] ne $location || [$inst getOrient] ne $orient} {error "unrelated existing placement changed"}
 $inst setPlacementStatus $status
}
foreach inst $added {$inst setPlacementStatus LOCKED}
puts "R166_EXTRACTED_SHARED_INPUT_ECO=$serial"
