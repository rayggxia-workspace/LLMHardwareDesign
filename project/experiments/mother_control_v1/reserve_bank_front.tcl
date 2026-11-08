# Temporarily reserve bank-front placement, excluding all actual fixed cells.
set block [ord::get_db_block]
set rectangles {}
set banks 0
foreach bank [$block getInsts] {
 if {[[$bank getMaster] getName] ne "s_sram_256x128_freepdk45"} {continue}
 set b [$bank getBBox]
 lappend rectangles [list [expr {[$b xMin]-4000}] [expr {[$b yMin]-28800}] [expr {[$b xMax]+4000}] [$b yMin]]
 incr banks
}
if {$banks!=4} {error "Expected four bank fronts"}
foreach inst [$block getInsts] {
 if {[$inst getPlacementStatus] ni {FIRM LOCKED COVER}} {continue}
 set b [$inst getBBox]
 set cuts {}
 foreach rect $rectangles {
  lassign $rect x0 y0 x1 y1
  set cx0 [expr {max($x0,[$b xMin]-10)}];set cy0 [expr {max($y0,[$b yMin]-10)}]
  set cx1 [expr {min($x1,[$b xMax]+10)}];set cy1 [expr {min($y1,[$b yMax]+10)}]
  if {$cx0>=$cx1 || $cy0>=$cy1} {lappend cuts $rect;continue}
  if {$x0<$cx0} {lappend cuts [list $x0 $y0 $cx0 $y1]}
  if {$cx1<$x1} {lappend cuts [list $cx1 $y0 $x1 $y1]}
  if {$y0<$cy0} {lappend cuts [list $cx0 $y0 $cx1 $cy0]}
  if {$cy1<$y1} {lappend cuts [list $cx0 $cy1 $cx1 $y1]}
 }
 set rectangles $cuts
}
set stream [open $mc_bank_reservation_inventory w]
foreach rect $rectangles {
 lassign $rect x0 y0 x1 y1
 odb::dbBlockage_create $block $x0 $y0 $x1 $y1
 puts $stream [join $rect "\t"]
}
close $stream
if {[llength $rectangles]==0} {error "No bank-front placement left"}
puts "MC_TEMP_BANK_FRONT_RECTANGLES [llength $rectangles]"
