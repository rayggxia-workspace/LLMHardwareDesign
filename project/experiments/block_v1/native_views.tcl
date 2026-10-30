# Independent native-tool readback; no design repair or generation here.
set matches {}
foreach lib [[ord::get_db] getLibs] {
  foreach master [$lib getMasters] {
    if {[$master getName] eq $wanted_master} {lappend matches $master}
  }
}
if {[llength $matches]!=1} {error "Missing or ambiguous generated LEF master"}
set master [lindex $matches 0]
set stream [open lef-interface.tsv w]
puts $stream "width\t[$master getWidth]"
puts $stream "height\t[$master getHeight]"
foreach term [$master getMTerms] {
  puts $stream "term\t[$term getName]\t[$term getIoType]\t[$term getSigType]"
  foreach pin [$term getMPins] {
    foreach box [$pin getGeometry] {
      if {[$box isVia]} {error "Unexpected via in generated abstract pin"}
      puts $stream "box\t[$term getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
    }
  }
}
foreach box [$master getObstructions] {
  if {[$box isVia]} {error "Unexpected via obstruction in generated abstract"}
  puts $stream "obstruction\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
}
close $stream
source $lib_interface_script
