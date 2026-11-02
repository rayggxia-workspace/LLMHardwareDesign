# Read-only final signal-pin geometry and added input-buffer supply snapshot.
set_thread_count 1
read_db $::env(INPUT_ODB)
set block [ord::get_db_block]
set out [open $::env(OUTPUT_IO_TSV) w]
puts $out "DBU\\t[$block getDbUnitsPerMicron]"
foreach term [$block getBTerms] {
 if {[$term getSigType] in {POWER GROUND}} {continue}
 foreach pin [$term getBPins] {
  foreach box [$pin getBoxes] {
   puts $out "PIN\\t[$term getName]\\t[$term getIoType]\\t[[$box getTechLayer] getName]\\t[$box xMin]\\t[$box yMin]\\t[$box xMax]\\t[$box yMax]"
  }
 }
}
set count 0
foreach inst [$block getInsts] {
 if {![string match {r157_io_*} [$inst getName]]} {continue}
 if {[[$inst getMaster] getName] ne "BUF_X16"} {error "unexpected IO buffer master"}
 foreach pg {VDD VSS} {
  set pin [$inst findITerm $pg]
  if {$pin eq "NULL" || [$pin getNet] eq "NULL"} {error "unconnected buffer supply: [$inst getName]/$pg"}
  if {[[$pin getNet] getName] ne $pg} {error "wrong buffer supply: [$inst getName]/$pg"}
 }
 lassign [$inst getLocation] x y
 puts $out "BUF\\t[$inst getName]\\t[[$inst getMaster] getName]\\t[$inst getPlacementStatus]\\tVDD\\tVSS\\t$x\\t$y"
 incr count
}
puts $out "BUFFER_COUNT\\t$count"
close $out
if {$count!=$::env(EXPECTED_IO_BUFFERS)} {error "wrong final IO buffer count: $count"}
