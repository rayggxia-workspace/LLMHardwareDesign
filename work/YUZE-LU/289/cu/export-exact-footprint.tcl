read_db $::env(CU_SOURCE_ODB)
set block [ord::get_db_block]
set f [open $::env(CU_FOOTPRINT_TCL) w]
puts $f {set fp_block [ord::get_db_block]}
set count 0
foreach bt [$block getBTerms] {
 if {[$bt getSigType] in {POWER GROUND}} {continue}
 puts $f [format {set fp_bt [$fp_block findBTerm %s]} [list [$bt getName]]]
 puts $f [format {if {$fp_bt eq "NULL"} {error %s}} [list "Missing original signal port [$bt getName]"]]
 puts $f {foreach fp_old [$fp_bt getBPins] {odb::dbBPin_destroy $fp_old}}
 foreach bp [$bt getBPins] {
  puts $f {set fp_bp [odb::dbBPin_create $fp_bt]}
  puts $f [format {$fp_bp setPlacementStatus %s} [list [$bp getPlacementStatus]]]
  foreach box [$bp getBoxes] {
   puts $f [format {odb::dbBox_create $fp_bp [[ord::get_db_tech] findLayer %s] %s %s %s %s} [list [[$box getTechLayer] getName]] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
  }
 }
 incr count
}
puts $f [list puts "Restored $count exact original signal BTerm geometries"]
close $f
puts "EXPORTED_ORIGINAL_SIGNAL_BTERMS $count"
