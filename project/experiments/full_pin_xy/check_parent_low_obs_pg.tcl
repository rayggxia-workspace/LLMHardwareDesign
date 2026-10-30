# Exact overlap screen of real parent PG, including every via landing, against
# the newly conservative M1-M3 OBS. Full rule spacing remains a separate gate.
if {![stage conservative_low_OBS_actual_PG_clear {
 set tested 0;set b [ord::get_db_block]
 foreach n [$b getNets] {
  if {[$n getSigType] ni {POWER GROUND}} {continue}
  foreach sw [$n getSWires] {foreach r [$sw getWires] {
   set shapes {}
   if {[$r isVia]} {
    set v [$r getTechVia];if {$v eq "NULL"} {set v [$r getBlockVia]}
    if {$v eq "NULL"} {error "Actual PG via has no resolved master"}
    lassign [$r getViaXY] vx vy
    foreach z [$v getBoxes] {lappend shapes [list [[$z getTechLayer] getName] [expr {$vx+[$z xMin]}] [expr {$vy+[$z yMin]}] [expr {$vx+[$z xMax]}] [expr {$vy+[$z yMax]}]]}
   } else {lappend shapes [list [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]]}
   foreach z $shapes {
    lassign $z layer x0 y0 x1 y1
    if {$layer ni {metal1 metal2 metal3}} {continue}
    foreach e $conservative_low_obstruction_envelopes {
     lassign $e name ly a c d f;if {$ly ne $layer} {continue}
     set i [$b findInst $name];if {[$i getOrient] ne "R0"} {error "Unsupported PG transform"}
     lassign [$i getLocation] ix iy
     if {$x0<$ix+$d && $ix+$a<$x1 && $y0<$iy+$f && $iy+$c<$y1} {error "Actual parent PG overlaps conservative OBS: $name $ly $z"}
     incr tested
    }
   }
  }}
 };puts "ACTUAL_PARENT_PG_VS_CONSERVATIVE_OBS_TESTS $tested"
}]} {close $stages;exit 1}
