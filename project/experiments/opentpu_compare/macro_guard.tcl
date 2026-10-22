# Isolate an immutable macro output from a long routed parent net. R0, zero
# master origin and fixed macro placement are already part of this experiment.
proc llhd_guard_macro_output {pin serial} {
  set block [ord::get_db_block]
  set slash [string last / $pin]
  set inst [$block findInst [string range $pin 0 [expr {$slash-1}]]]
  set port [string range $pin [expr {$slash+1}] end]
  set term [$inst findITerm $port]
  if {$term eq "NULL" || [$term getIoType] ne "OUTPUT"} {error "Not a macro output: $pin"}
  if {[$inst getOrient] ne "R0"} {error "Unsupported macro orientation: $pin"}
  set master [$inst getMaster]
  lassign [$master getOrigin] ox oy
  if {$ox != 0 || $oy != 0} {error "Unsupported macro origin: $pin"}
  lassign [$inst getLocation] ix iy
  set bbox [$inst getBBox]
  set xmin [$bbox xMin]; set xmax [$bbox xMax]
  set ymin [$bbox yMin]; set ymax [$bbox yMax]
  set shapes {}
  foreach mpin [[$term getMTerm] getMPins] {
    foreach shape [$mpin getGeometry] {
      if {[$shape getTechLayer] eq "NULL"} {continue}
      set px [expr {$ix+([$shape xMin]+[$shape xMax])/2.0}]
      set py [expr {$iy+([$shape yMin]+[$shape yMax])/2.0}]
      foreach side {left right bottom top} distance [list [expr {$px-$xmin}] [expr {$xmax-$px}] [expr {$py-$ymin}] [expr {$ymax-$py}]] {
        lappend shapes [list $distance $side $px $py]
      }
    }
  }
  if {![llength $shapes]} {error "Macro output has no physical pin shape: $pin"}
  lassign [lindex [lsort -real -index 0 $shapes] 0] distance side px py
  set buffer [[ord::get_db] findMaster BUF_X2]
  set width [$buffer getWidth]; set height [$buffer getHeight]
  set dbu [$block getDbUnitsPerMicron]
  set gap [expr {2.0*$dbu}]
  set x [expr {$px-$width/2.0}]; set y [expr {$py-$height/2.0}]
  switch $side {
    left {set x [expr {$xmin-$gap-$width}]}
    right {set x [expr {$xmax+$gap}]}
    bottom {set y [expr {$ymin-$gap-$height}]}
    top {set y [expr {$ymax+$gap}]}
  }
  set name llhd_macro_guard_${serial}
  if {[$block findInst $name] ne "NULL"} {error "Duplicate guard instance $name"}
  set net [$term getNet]
  if {$net eq "NULL"} {error "Unconnected macro output: $pin"}
  set location [list [expr {$x/$dbu}] [expr {$y/$dbu}]]
  insert_buffer -buffer_cell BUF_X2 -net [$net getName] -location $location -buffer_name $name -net_name ${name}_net
  set added [$block findInst $name]
  if {$added eq "NULL"} {error "Buffer insertion failed: $pin"}
  $added setLocation [expr {int(round($x))}] [expr {int(round($y))}]
  $added setPlacementStatus PLACED
  puts "MACRO_OUTPUT_GUARD $pin $name side=$side location_um=$location pin_depth_um=[expr {$distance/$dbu}]"
  return [list $pin $name BUF_X2 $side {*}$location]
}
