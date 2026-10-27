# Prefabrication-only protection, charged to the final physical inventory.
# The actual GDS/Liberty ANTENNA_X1 is used without changing platform metadata.
set block [ord::get_db_block]
set master [[ord::get_db] findMaster ANTENNA_X1]
if {$master eq "NULL"} {error "Actual ANTENNA_X1 is unavailable"}
set sta_nets [dict create]
foreach net [get_nets *] {dict set sta_nets [get_full_name $net] $net}
set stream [open $::env(RESULTS_DIR)/bv1-input-diodes.tsv w]
set count 0
foreach port [$block getBTerms] {
  if {[$port getSigType] in {POWER GROUND} || [$port getIoType] ne "INPUT"} {continue}
  if {[$port getName] eq "clk"} {continue}
  set net [$port getNet]
  if {$net eq "NULL"} {error "Unconnected input port"}
  set net_name [$net getName]
  if {![dict exists $sta_nets $net_name]} {error "Exact STA input net missing: $net_name"}
  set loads {}
  foreach term [$net getITerms] {
    if {[[$term getMTerm] getIoType] eq "INPUT" && [[$term getMTerm] getSigType] ni {POWER GROUND}} {
      lappend loads $term
    }
  }
  # A used port must already have its original CTS/input load. Do not create
  # protection on floating or unused interfaces to hide a missing connection.
  if {[llength $loads]==0} {continue}
  set anchor [[lindex $loads 0] getInst]
  lassign [$anchor getLocation] x y
  set name bv1_input_diode_$count
  if {[$block findInst $name] ne "NULL"} {error "Duplicate protection instance"}
  set inst [odb::dbInst_create $block $master $name]
  $inst setLocation $x $y
  $inst setOrient [$anchor getOrient]
  $inst setPlacementStatus PLACED
  set input [$inst findITerm A]
  if {$input eq "NULL"} {error "Protection input A missing"}
  $input connect $net
  foreach term [$inst getITerms] {
    set kind [[$term getMTerm] getSigType]
    if {$kind in {POWER GROUND}} {
      set supply [expr {$kind eq "POWER" ? "VDD" : "VSS"}]
      set power [$block findNet $supply]
      if {$power eq "NULL"} {error "Original supply missing: $supply"}
      $term connect $power
    }
  }
  set_dont_touch [get_cells $name]
  # Prevent hold repair from moving the protection behind a new root buffer.
  # Repairs downstream of the original first buffer remain available.
  set_dont_touch [dict get $sta_nets $net_name]
  puts $stream "$name\t[$port getName]\t$net_name\t[$anchor getName]"
  incr count
}
close $stream
if {$count==0} {error "No used nonclock input protection was instantiated"}
global_connect
detailed_placement_helper
check_placement -verbose
set checked 0
set stream [open $::env(RESULTS_DIR)/bv1-input-diodes-placed.tsv w]
foreach inst [$block getInsts] {
  if {[[$inst getMaster] getName] ne "ANTENNA_X1"} {continue}
  set term [$inst findITerm A]
  if {[$term getNet] eq "NULL"} {error "Protection lost its root connection"}
  puts $stream "[$inst getName]\t[[$term getNet] getName]\t[$inst getLocation]\t[$inst getOrient]\t[$inst getPlacementStatus]"
  incr checked
}
close $stream
if {$checked!=$count} {error "Unexpected diode inventory"}
puts "BV1_INPUT_DIODES count=$count area_um2=[expr {$count*0.266}] input_cap_ff=[expr {$count*0.023429}]"
