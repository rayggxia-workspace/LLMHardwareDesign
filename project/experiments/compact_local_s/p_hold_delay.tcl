# Used only for S_P after final RC exposed hold failures on load_valid and
# load_b_base[6], with adjacent bits [3] and [4] also near the boundary.
proc sram_delay_input {port_name stages prefix} {
set block [ord::get_db_block]
set port [$block findBTerm $port_name]
if {$port eq "NULL" || [$port getIoType] ne "INPUT"} {error "Expected feeder-control input"}
set root [$port getNet]
set loads {}
foreach term [$root getITerms] {
  if {[[[$term getInst] getMaster] getName] eq "ANTENNA_X1"} {continue}
  if {[[$term getMTerm] getIoType] ne "INPUT"} {error "Unexpected feeder-control internal driver"}
  lappend loads $term
}
if {[llength $loads]==0} {error "No actual functional feeder-control load"}
set anchor [[lindex $loads 0] getInst]
lassign [$anchor getLocation] ax ay
set master [[ord::get_db] findMaster BUF_X1]
set current $root
set stream [open $::env(RESULTS_DIR)/${prefix}-buffers.tsv w]
for {set stage 0} {$stage<$stages} {incr stage} {
  set name ${prefix}_$stage
  set net_name ${prefix}_net_$stage
  if {[$block findInst $name] ne "NULL" || [$block findNet $net_name] ne "NULL"} {error "Duplicate feeder hold repair"}
  set inst [odb::dbInst_create $block $master $name]
  set next [odb::dbNet_create $block $net_name]
  $inst setLocation [expr {$ax+$stage*[$master getWidth]}] $ay
  $inst setOrient [$anchor getOrient]
  $inst setPlacementStatus PLACED
  [$inst findITerm A] connect $current
  [$inst findITerm Z] connect $next
  foreach term [$inst getITerms] {
    set kind [[$term getMTerm] getSigType]
    if {$kind in {POWER GROUND}} {
      set supply [expr {$kind eq "POWER" ? "VDD" : "VSS"}]
      set power [$block findNet $supply]
      if {$power eq "NULL"} {error "Original supply missing"}
      $term connect $power
    }
  }
  set_dont_touch [get_cells $name]
  puts $stream "$name\t[$current getName]\t[$next getName]"
  set current $next
}
close $stream
foreach term $loads {$term disconnect; $term connect $current}
foreach term [$root getITerms] {
  if {[[[$term getInst] getMaster] getName] eq "ANTENNA_X1" && [$term getNet] ne $root} {error "Port protection root changed"}
}
}
foreach {port prefix} {
    {load_valid} compact_delay_load_valid
    {load_b_base[3]} compact_delay_b3
    {load_b_base[4]} compact_delay_b4
    {load_b_base[6]} compact_delay_b6
} {
    sram_delay_input $port $compact_delay_stages $prefix
}
global_connect
detailed_placement_helper
check_placement -verbose
