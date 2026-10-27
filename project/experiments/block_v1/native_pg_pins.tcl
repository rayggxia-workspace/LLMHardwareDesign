# Independent native readback of explicitly typed supply ports. Signal scoped
# readback remains the separately controlled native_lib_pins.tcl contract.
set cell [get_lib_cells ${wanted_library}/${wanted_master}]
if {[llength $cell]!=1} {error "Ambiguous PG cell"}
set cell [lindex $cell 0]
set stream [open lib-pg-interface.tsv w]
foreach {name direction} {VDD power VSS ground} {
  set port [$cell find_liberty_port $name]
  if {![$port is_pwr_gnd]} {error "Supply is an ordinary signal port"}
  set actual [get_property $port direction]
  if {$actual ne $direction} {error "Incorrect typed supply role"}
  puts $stream "$name\t$actual\t[$port is_pwr_gnd]"
}
close $stream
