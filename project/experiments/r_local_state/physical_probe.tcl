# Read-only final physical connectivity and locality evidence.
set_thread_count 1
read_db $::env(INPUT_ODB)
set block [ord::get_db_block]
set out [open $::env(OUTPUT_TSV) w]
puts $out "DBU\t[$block getDbUnitsPerMicron]"
set bad 0;set pg 0;set signals 0;set shapes 0
foreach inst [$block getInsts] {
 foreach term [$inst getITerms] {
  set sig [[$term getMTerm] getSigType]
  if {$sig ni {POWER GROUND}} {continue}
  incr pg
  set net [$term getNet]
  if {$net eq "NULL" || [$net getSigType] ne $sig} {incr bad;puts $out "BADPG\t[$inst getName]\t[[$term getMTerm] getName]"}
 }
}
foreach term [$block getBTerms] {
 if {[$term getSigType] in {POWER GROUND}} {continue}
 incr signals
 foreach pin [$term getBPins] {foreach box [$pin getBoxes] {
  incr shapes
  puts $out "PIN\t[$term getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
 }}
}
foreach region [$block getRegions] {
 set boxes {}
 foreach box [$region getBoundaries] {lappend boxes [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}
 set n 0;set outside 0
 foreach inst [$region getRegionInsts] {
  incr n;set ib [$inst getBBox];set inside 0
  foreach b $boxes {lassign $b x0 y0 x1 y1;if {[$ib xMin]>=$x0 && [$ib yMin]>=$y0 && [$ib xMax]<=$x1 && [$ib yMax]<=$y1} {set inside 1}}
  if {!$inside} {incr outside}
 }
 puts $out "REGION\t[$region getName]\t$n\t$outside\t$boxes"
}
puts $out "SUMMARY\t$signals\t$shapes\t$pg\t$bad"
close $out
if {$bad!=0 || $pg==0 || $signals!=821 || $shapes!=821} {error "final pin or supply evidence failed"}
