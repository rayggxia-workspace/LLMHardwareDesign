# Runs through the Tcl OpenDB API; this installed OpenROAD has no Python API.
read_db overlay.odb
set tech [ord::get_db_tech]
set expected {}
for {set i 1} {$i <= 12} {incr i} { lappend expected metal$i }
set layers {}
foreach layer [$tech getLayers] {
  if {[$layer getRoutingLevel] > 0} { lappend layers [$layer getName] }
}
if {$layers ne $expected} { error "routing stack mismatch: $layers" }
set stream [open database.json w]
puts $stream "{\"routing_layers\":\[\"[join $layers {","}]\"\],"
puts $stream "\"dbu_per_um\":[$tech getDbUnitsPerMicron],\"vias\":\["
set separator ""
foreach name {BV1_via10 BV1_via11} {
  set via [$tech findVia $name]
  if {$via eq "NULL" || $via eq ""} { error "missing custom via $name" }
  if {[$via getResistance] <= 0} { error "missing via resistance" }
  set boxes [$via getBoxes]
  if {[llength $boxes] != 3} { error "expected two enclosures and one cut" }
  puts -nonewline $stream "$separator{\"name\":\"$name\",\"resistance_ohm\":[$via getResistance],\"boxes\":\["
  set inner ""
  foreach box $boxes {
    set lname [[$box getTechLayer] getName]
    puts -nonewline $stream "$inner\[\"$lname\",[$box xMin],[$box yMin],[$box xMax],[$box yMax]\]"
    set inner ","
  }
  puts -nonewline $stream "\]}"
  set separator ","
}
puts $stream "\]}"
close $stream
set stream [open capabilities.json w]
puts $stream "\{"
set separator ""
foreach command {bench_wires gen_solver_patterns gen_rcx_model solve_capacitance set_field_solver_permittivity add_field_solver_box} {
  set present [expr {[llength [info commands $command]] > 0}]
  puts -nonewline $stream "$separator\"$command\":$present"
  set separator ","
}
puts $stream "\}"
close $stream
puts "PASS_RESEARCH12_DATABASE_READBACK_ONLY"
