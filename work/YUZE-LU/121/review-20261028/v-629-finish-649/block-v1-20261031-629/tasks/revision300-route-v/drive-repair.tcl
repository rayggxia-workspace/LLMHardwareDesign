global_route -start_incremental
proc drive_signal_pins {i} {
  set result {}
  foreach t [$i getITerms] {
    set m [$t getMTerm]
    if {[$m getSigType] in {POWER GROUND}} {continue}
    set n [$t getNet]
    lappend result [list [$m getName] [expr {$n eq "NULL" ? "NULL" : [$n getName]}]]
  }
  return [lsort $result]
}
set b [ord::get_db_block]
set i [$b findInst {place84364}]
if {$i eq "NULL" || [[$i getMaster] getName] ne "BUF_X2"} {error "Unexpected current V measured driver place84364"}
set pins [drive_signal_pins $i]
set replacement [[ord::get_db] findMaster BUF_X4]
if {$replacement eq "NULL" || ![$i swapMaster $replacement]} {error "Native driver swap failed place84364"}
if {[drive_signal_pins $i] ne $pins} {error "Driver signal pin/net identity changed place84364"}
puts "MEASURED_DRIVE_SWAP place84364 BUF_X2 BUF_X4"
set i [$b findInst {place76249}]
if {$i eq "NULL" || [[$i getMaster] getName] ne "BUF_X1"} {error "Unexpected current V measured driver place76249"}
set pins [drive_signal_pins $i]
set replacement [[ord::get_db] findMaster BUF_X2]
if {$replacement eq "NULL" || ![$i swapMaster $replacement]} {error "Native driver swap failed place76249"}
if {[drive_signal_pins $i] ne $pins} {error "Driver signal pin/net identity changed place76249"}
puts "MEASURED_DRIVE_SWAP place76249 BUF_X1 BUF_X2"
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
set_dont_touch [get_cells {place84364}]
set_dont_touch [get_cells {place76249}]
detailed_placement_helper
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
