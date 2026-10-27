# Read-only final database audit; power checks do not optimize the database.
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db $::env(BV1_ODB)
set block [ord::get_db_block]
set stream [open physical-summary.tsv w]
puts $stream "dbu\t[$block getDbUnitsPerMicron]"
set die [$block getDieArea]
puts $stream "die\t[$die xMin]\t[$die yMin]\t[$die xMax]\t[$die yMax]"
set core [$block getCoreArea]
puts $stream "core\t[$core xMin]\t[$core yMin]\t[$core xMax]\t[$core yMax]"
set masters [dict create]
set unplaced 0
set incorrect_pg 0
set pg_terms 0
set open_inputs 0
foreach inst [$block getInsts] {
  set master [$inst getMaster]
  set signal_master 0
  foreach term [$master getMTerms] {
    if {[$term getSigType] ni {POWER GROUND}} {set signal_master 1}
  }
  set key "[$master getName]\t[$master getType]\t$signal_master\t[$master getWidth]\t[$master getHeight]"
  dict incr masters $key
  if {[$inst getPlacementStatus] ni {PLACED FIRM LOCKED COVER}} {incr unplaced}
  foreach term [$inst getITerms] {
    set definition [$term getMTerm]
    set kind [$definition getSigType]
    set net [$term getNet]
    if {$kind in {POWER GROUND}} {
      incr pg_terms
      set expected [expr {$kind eq "POWER" ? "VDD" : "VSS"}]
      if {$net eq "NULL" || [$net getName] ne $expected} {incr incorrect_pg}
    } elseif {[$definition getIoType] in {INPUT INOUT} && $net eq "NULL"} {incr open_inputs}
  }
}
puts $stream "unplaced\t$unplaced"
puts $stream "incorrect_pg_iterms\t$incorrect_pg"
puts $stream "pg_iterm_count\t$pg_terms"
puts $stream "open_signal_inputs\t$open_inputs"
foreach supply {VDD VSS} {
  set code [catch {check_power_grid -net $supply -error_file ${supply}-errors.rpt} value]
  set valid [expr {$code==0 && [string is boolean -strict $value] && $value}]
  puts $stream "pg_$supply\t$valid"
  puts "NATIVE_PG $supply code=$code return=<$value> pass=$valid"
}
set tech [[ord::get_db] getTech]
set levels {}
foreach layer [$tech getLayers] {
  if {[$layer getRoutingLevel]>0} {lappend levels [$layer getName]}
}
puts $stream "routing_layers\t[join $levels ,]"
close $stream
set stream [open physical-masters.tsv w]
dict for {key count} $masters {puts $stream "$key\t$count"}
close $stream
set stream [open physical-input-diodes.tsv w]
foreach inst [$block getInsts] {
  if {[[$inst getMaster] getName] ne "ANTENNA_X1"} {continue}
  set term [$inst findITerm A]
  set net [$term getNet]
  if {$net eq "NULL"} {error "Unconnected actual diode"}
  puts $stream "[$inst getName]\t[$net getName]"
}
close $stream
set stream [open physical-pins.tsv w]
foreach term [$block getBTerms] {
  if {[$term getSigType] in {POWER GROUND}} {continue}
  foreach pin [$term getBPins] {
    foreach box [$pin getBoxes] {
      puts $stream "[$term getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
    }
  }
}
close $stream
