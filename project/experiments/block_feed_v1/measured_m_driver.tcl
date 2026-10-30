# Guarded driver-only sizing; caller owns one incremental route session.
set block [ord::get_db_block]
set inst [$block findInst hold40391]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne "CLKBUF_X1"} {error "Measured M driver identity changed"}
proc feed_pin_snapshot {inst} {
 set pins {}
 foreach term [$inst getITerms] {
  set def [$term getMTerm]
  if {[$def getSigType] in {POWER GROUND}} {continue}
  set net [$term getNet]
  if {$net eq "NULL"} {error "Open measured driver pin"}
  lappend pins [list [$def getName] [$def getIoType] [$net getName]]
 }
 return [lsort $pins]
}
set old [feed_pin_snapshot $inst]
set master [[ord::get_db] findMaster CLKBUF_X2]
if {$master eq "NULL" || ![$inst swapMaster $master]} {error "Measured M sizing failed"}
if {[feed_pin_snapshot $inst] ne $old} {error "Measured buffer signal identity changed"}
foreach term [$inst getITerms] {
 set kind [[$term getMTerm] getSigType]
 if {$kind in {POWER GROUND}} {
  set name [expr {$kind eq "POWER" ? "VDD" : "VSS"}]
  set net [$block findNet $name]
  if {$net eq "NULL"} {error "Original PG missing"}
  $term connect $net
 }
}
global_connect
set_dont_touch [get_cells hold40391]
