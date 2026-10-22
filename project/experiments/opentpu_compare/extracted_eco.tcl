# A real extracted critical wire needs a repeater, rather than only a stronger
# driver: split its length while preserving every original sink and BTerm.
proc llhd_repeat_driver {pin master_name serial} {
  set block [ord::get_db_block]
  set slash [string last / $pin]
  set inst [$block findInst [string range $pin 0 [expr {$slash-1}]]]
  if {$inst eq "NULL"} {error "Missing repeater driver $pin"}
  set term [$inst findITerm [string range $pin [expr {$slash+1}] end]]
  if {$term eq "NULL" || [$term getIoType] ne "OUTPUT"} {error "Not an output $pin"}
  set net [$term getNet]
  if {$net eq "NULL" || [$net getSigType] in {POWER GROUND CLOCK}} {error "Not a data net $pin"}
  lassign [$inst getLocation] dx dy
  set points {}
  foreach load [$net getITerms] {
    if {[$load getIoType] eq "INPUT"} {lappend points [[$load getInst] getLocation]}
  }
  foreach port [$net getBTerms] {
    foreach bp [$port getBPins] {foreach box [$bp getBoxes] {
      lappend points [list [expr {([$box xMin]+[$box xMax])/2.0}] [expr {([$box yMin]+[$box yMax])/2.0}]]
    }}
  }
  if {[llength $points]!=1} {error "Critical repeater requires exactly one physical sink: $pin"}
  lassign [lindex $points 0] lx ly
  set x [expr {int(round(($dx+$lx)/2.0))}]
  set y [expr {int(round(($dy+$ly)/2.0))}]
  set name llhd_extracted_repeater_${serial}
  if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_net] ne "NULL"} {error "ECO name collision"}
  set master [[ord::get_db] findMaster $master_name]
  if {$master eq "NULL"} {error "Missing buffer master $master_name"}
  if {![regexp {^BUF_X(1|2|4|8|16|32)$} $master_name]} {error "Repeater must be a non-inverting buffer"}
  # A geometric midpoint may fall inside a fixed hard macro. Seed immediately
  # outside its nearest edge before asking the native legalizer to snap rows.
  set gap [expr {2*[$block getDbUnitsPerMicron]}]
  foreach obstacle [$block getInsts] {
    if {![string match llhd_* [[$obstacle getMaster] getName]]} {continue}
    set bb [$obstacle getBBox]
    if {$x>=[$bb xMin]-[$master getWidth] && $x<=[$bb xMax] && $y>=[$bb yMin]-[$master getHeight] && $y<=[$bb yMax]} {
      set choices [list [list [expr {$x-[$bb xMin]}] [expr {[$bb xMin]-$gap-[$master getWidth]}] $y] \
                        [list [expr {[$bb xMax]-$x}] [expr {[$bb xMax]+$gap}] $y] \
                        [list [expr {$y-[$bb yMin]}] $x [expr {[$bb yMin]-$gap-[$master getHeight]}]] \
                        [list [expr {[$bb yMax]-$y}] $x [expr {[$bb yMax]+$gap}]]]
      lassign [lindex [lsort -real -index 0 $choices] 0] distance x y
    }
  }
  set short [odb::dbNet_create $block ${name}_net]
  set added [odb::dbInst_create $block $master $name]
  $short setSigType SIGNAL
  odb::dbITerm_disconnect $term
  odb::dbITerm_connect $term $short
  odb::dbITerm_connect [$added findITerm A] $short
  odb::dbITerm_connect [$added findITerm Z] $net
  if {[$term getNet] ne $short || [[$added findITerm Z] getNet] ne $net} {error "Repeater wiring mismatch"}
  $added setOrient R0
  $added setLocation $x $y
  $added setPlacementStatus PLACED
  return [list $pin $name $master_name $x $y]
}

# Isolate a top-level input without moving its BPin or changing its constraint.
# All original input loads move together; no state or functional logic changes.
proc llhd_delay_input {port_name serial} {
  set block [ord::get_db_block]
  set port [$block findBTerm $port_name]
  if {$port eq "NULL" || [$port getIoType] ne "INPUT" || $port_name eq "clk"} {error "Not a data input $port_name"}
  set net [$port getNet]
  set loads [$net getITerms]
  foreach load $loads {if {[$load getIoType] ne "INPUT"} {error "Unexpected input net driver"}}
  set boxes {}
  foreach bp [$port getBPins] {foreach box [$bp getBoxes] {lappend boxes $box}}
  if {[llength $boxes]!=1} {error "Expected exactly one fixed BPin box"}
  set box [lindex $boxes 0];set dbu [$block getDbUnitsPerMicron]
  set core [$block getCoreArea]
  set x [expr {([$box xMin]+[$box xMax])/2.0}]
  set y [expr {([$box yMin]+[$box yMax])/2.0}]
  set x [expr {int(max([$core xMin]+2*$dbu,min([$core xMax]-2*$dbu,$x)))}]
  set y [expr {int(max([$core yMin]+2*$dbu,min([$core yMax]-2*$dbu,$y)))}]
  set name llhd_extracted_input_${serial}
  if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_net] ne "NULL"} {error "ECO name collision"}
  set after [odb::dbNet_create $block ${name}_net]
  set added [odb::dbInst_create $block [[ord::get_db] findMaster BUF_X2] $name]
  $after setSigType SIGNAL
  foreach load $loads {odb::dbITerm_disconnect $load;odb::dbITerm_connect $load $after}
  odb::dbITerm_connect [$added findITerm A] $net
  odb::dbITerm_connect [$added findITerm Z] $after
  if {[$port getNet] ne $net || [llength [$net getITerms]]!=1 || [llength [$after getITerms]]!=[llength $loads]+1} {error "Input guard wiring mismatch"}
  $added setOrient R0
  $added setLocation $x $y
  $added setPlacementStatus PLACED
  return [list $port_name $name BUF_X2 $x $y]
}
