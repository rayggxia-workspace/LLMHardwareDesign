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
  while {[$block findInst $name] ne "NULL" || [$block findNet ${name}_net] ne "NULL"} {
    incr serial
    set name llhd_macro_guard_${serial}
  }
  set net [$term getNet]
  if {$net eq "NULL"} {error "Unconnected macro output: $pin"}
  set location [list [expr {$x/$dbu}] [expr {$y/$dbu}]]
  puts "GUARD_REQUEST $pin net=[$net getName] location=$location"
  # Explicit native ODB edit avoids the crashing Resizer insertion helper
  # after a fresh GRT reload. Keep every original load on its original net;
  # only the macro driver moves to the new short macro->BUF input net.
  if {[$net getSigType] in {POWER GROUND}} {error "Non-signal macro output: $pin"}
  set short [odb::dbNet_create $block ${name}_net]
  set added [odb::dbInst_create $block $buffer $name]
  if {$added eq "NULL"} {error "Buffer insertion failed: $pin"}
  if {$short eq "NULL"} {error "Buffer short net creation failed: $pin"}
  $short setSigType [$net getSigType]
  set input [$added findITerm A]
  set output [$added findITerm Z]
  if {$input eq "NULL" || $output eq "NULL"} {error "Unexpected BUF_X2 pin contract"}
  odb::dbITerm_disconnect $term
  odb::dbITerm_connect $term $short
  odb::dbITerm_connect $input $short
  odb::dbITerm_connect $output $net
  if {[$term getNet] ne $short || [$input getNet] ne $short || [$output getNet] ne $net} {error "Guard wiring contract failed: $pin"}
  $added setOrient R0
  $added setLocation [expr {int(round($x))}] [expr {int(round($y))}]
  $added setPlacementStatus PLACED
  puts "MACRO_OUTPUT_GUARD $pin $name side=$side location_um=$location pin_depth_um=[expr {$distance/$dbu}]"
  return [list $pin $name BUF_X2 $side {*}$location]
}
