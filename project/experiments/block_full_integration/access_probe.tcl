# Read-only input probe for fixed access pads below customizable routing layers.
# Run in allocated job; HPY_ACCESS_ODB points to the qualified derived macro.
# No database writes and no routing/placement/repair commands.
proc esc {s} {return [string map [list \\ \\\\ \t \\t \n \\n \r \\r] $s]}
proc emit {args} {
  set fields {}
  foreach x $args {lappend fields [esc $x]}
  puts [join $fields "\t"]
}
proc query {object method args} {
  set code [catch {$object $method {*}$args} result]
  return [list $code $result]
}
if {![info exists ::env(HPY_ACCESS_ODB)]} {error "HPY_ACCESS_ODB required"}
set_thread_count 1
read_db $::env(HPY_ACCESS_ODB)
set db [ord::get_db]
set block [$db getChip]
set block [$block getBlock]
set tech [$db getTech]
emit HPY_ACCESS_SCHEMA 1
emit BLOCK [$block getName] DBU [$tech getDbUnitsPerMicron] GRID [$tech getManufacturingGrid]
foreach pattern {odb::dbBlock_*Track* odb::dbTrackGrid_* odb::dbMaster_*Symmetry* odb::dbBlock_*NonDefault* odb::dbTechNonDefaultRule_*} {
  emit API $pattern [info commands $pattern]
}
foreach layer [$tech getLayers] {
  if {[$layer getType] ne "ROUTING"} {continue}
  set name [$layer getName]
  emit LAYER $name [$layer getRoutingLevel] [$layer getWidth] [$layer getSpacing] [$layer getDirection]
  lassign [query $block findTrackGrid $layer] code track
  if {$code || $track eq "NULL"} {emit TRACK_MISSING $name $code $track;continue}
  foreach axis {X Y} {
    lassign [query $track getNumGridPatterns$axis] code count
    if {$code} {emit TRACK_PATTERN_ERROR $name $axis $code $count;continue}
    for {set i 0} {$i<$count} {incr i} {
      lassign [query $track getGridPattern$axis $i] code values
      emit TRACK_PATTERN $name $axis $i $code $values
    }
  }
}
set count 0
foreach bt [$block getBTerms] {
  set net [$bt getNet]
  set netname ""
  if {$net ne "NULL"} {set netname [$net getName]}
  foreach bp [$bt getBPins] {
    foreach box [$bp getBoxes] {
      if {[$box isVia]} {emit UNSUPPORTED_BPIN_VIA [$bt getName];continue}
      set layer [$box getTechLayer]
      if {$layer eq "NULL"} {emit UNSUPPORTED_BPIN_LAYER [$bt getName];continue}
      emit BPIN [$bt getName] $netname [$bt getIoType] [$bt getSigType] [$layer getName] \
        [$box xMin] [$box yMin] [$box xMax] [$box yMax]
      incr count
    }
  }
}
foreach lib [$db getLibs] {
  foreach master [$lib getMasters] {
    # Macro library symmetry cannot be inferred from a rectangular drawing.
    if {[$master getType] ne "BLOCK"} {continue}
    emit MASTER [$lib getName] [$master getName] [$master getWidth] [$master getHeight] \
      [query $master getSymmetryX] [query $master getSymmetryY] [query $master getSymmetryR90]
  }
}
lassign [query $block getNonDefaultRules] code rules
emit BLOCK_NDRS $code $rules
emit HPY_ACCESS_PROBE_COMPLETE BPIN_BOXES $count READ_ONLY true
