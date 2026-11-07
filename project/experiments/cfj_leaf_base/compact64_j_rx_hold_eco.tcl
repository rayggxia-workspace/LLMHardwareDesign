# Fixed receiver-only endpoint set from physical04 extracted hold analysis.
# Four original-library buffers per selected D input; no clock/SDC changes.
set block [ord::get_db_block]
set master [[ord::get_db] findMaster BUF_X1]
if {$master eq "NULL"} {error "BUF_X1 not found"}
set stream [open [file join [file dirname [info script]] rx-hold-targets.tsv] r]
set names {}
set count 0
while {[gets $stream line] >= 0} {
  lassign [split $line "\t"] endpoint original_slack
  if {![string match {services.rx_boundary.*/D} $endpoint]} {error "Unexpected endpoint $endpoint"}
  set instance [string range $endpoint 0 end-2]
  set sink [$block findInst $instance]
  if {$sink eq "NULL"} {
    set sink [$block findInst [string map [list {[} {\[} {]} {\]}] $instance]]
  }
  if {$sink eq "NULL"} {error "ECO endpoint not found: $endpoint"}
  set pin [$sink findITerm D]
  set previous [$pin getNet]
  if {$previous eq "NULL"} {error "Disconnected endpoint $endpoint"}
  set location [$sink getLocation]
  $pin disconnect
  for {set i 0} {$i < 4} {incr i} {
    set name cfj64_rxhold_${count}_$i
    if {[$block findInst $name] ne "NULL"} {error "ECO already applied"}
    set cell [odb::dbInst_create $block $master $name]
    set net [odb::dbNet_create $block ${name}_z]
    $cell setLocation {*}$location
    $cell setPlacementStatus PLACED
    [$cell findITerm A] connect $previous
    [$cell findITerm Z] connect $net
    set previous $net
    lappend names $name
  }
  $pin connect $previous
  puts "J64_RX_HOLD_ECO $endpoint original_slack=$original_slack four_BUF_X1"
  incr count
}
close $stream
if {$count != 301} {error "Unexpected target count: $count"}
# Power must connect before do-not-touch is applied.
global_connect
foreach name $names {set_dont_touch [get_cells $name]}
detailed_placement_helper
check_placement -verbose
