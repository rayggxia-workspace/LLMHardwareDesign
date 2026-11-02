read_db $::env(SRAM_STREAM_ODB)
set block [ord::get_db_block]
if {[$block getDbUnitsPerMicron] != 2000} {error "Unexpected native DBU"}
set f [open $::env(SRAM_STREAM_INVENTORY) w]
foreach inst [$block getInsts] {
  if {[$inst getPlacementStatus] eq "NONE"} {error "Unplaced stream component"}
  lassign [$inst getOrigin] ox oy
  lassign [$inst getLocation] x y
  puts $f "[$inst getName]\t[[$inst getMaster] getName]\t$ox\t$oy\t[$inst getOrient]\t$x\t$y"
}
close $f
