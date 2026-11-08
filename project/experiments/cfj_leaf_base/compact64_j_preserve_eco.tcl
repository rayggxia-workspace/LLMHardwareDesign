# Preserve the legalized T terminal bank and repair only from new extracted RC.
set block [ord::get_db_block]
set lease [$block findInst services.lease]
if {$lease eq "NULL"} {error "Pinned T instance not found"}
global_connect
set count 0
set resized {}
set report [open $::env(RESULTS_DIR)/j-terminal-drivers.tsv w]
foreach pin [$lease getITerms] {
  set port [[$pin getMTerm] getName]
  if {![regexp {^write_(data|index)\[[0-9]+\]$} $port]} {continue}
  set net [$pin getNet]
  set drivers {}
  foreach term [$net getITerms] {
    if {[$term getIoType] eq "OUTPUT"} {lappend drivers $term}
  }
  if {[llength $drivers] != 1} {error "Expected one terminal driver: $port"}
  set inst [[lindex $drivers 0] getInst]
  if {[[$inst getMaster] getName] ni {BUF_X16 BUF_X32}} {error "Terminal strength changed: $port"}
  if {[$inst getPlacementStatus] ne "FIRM"} {error "Terminal location is not pinned: $port"}
  if {$port eq {write_data[38]} || $port eq {write_data[36]}} {
    if {[replace_cell [get_cells [$inst getName]] BUF_X32] != 1} {error "Terminal resize rejected"}
    $inst setPlacementStatus PLACED
    lappend resized [$inst getName]
  }
  puts $report "$port\t[$inst getName]\t[[$inst getMaster] getName]"
  set_dont_touch [get_nets [$net getName]]
  incr count
}
if {$count != 138} {error "Unexpected terminal width: $count"}
close $report
detailed_placement_helper
check_placement -verbose
foreach name $resized {[$block findInst $name] setPlacementStatus FIRM}
# One-time parent access restrictions diagnosed from physical17 preflight.
# Keep the on-pin/right landing available; do not modify leaf geometry.
set tech [[ord::get_db] getTech]
odb::dbObstruction_create $block [$tech findLayer metal9] 2499000 1828000 2503600 1837000
odb::dbObstruction_create $block [$tech findLayer metal10] 2781600 1157000 2783360 1165000
puts "J64_PRESERVE_TERMINALS $count"
