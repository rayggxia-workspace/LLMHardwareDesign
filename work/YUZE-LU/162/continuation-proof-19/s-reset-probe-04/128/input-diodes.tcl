# Fixed-bottom input receivers, inserted before native global route.
# The external BUF_X2/load/clock contract remains unchanged.
set feed_block [ord::get_db_block]
set feed_master [[ord::get_db] findMaster BUF_X8]
if {$feed_master eq "NULL"} {error "Actual input receiver BUF_X8 is absent"}
set feed_count 0
set feed_report [open $::env(RESULTS_DIR)/feed-input-receivers.tsv w]
foreach port [$feed_block getBTerms] {
  if {[$port getSigType] in {POWER GROUND} || [$port getIoType] ne "INPUT" || [$port getName] eq "clk"} {continue}
  set net [$port getNet]
  if {$net eq "NULL" || [llength [$net getBTerms]]!=1} {error "Ambiguous input root"}
  set loads {}
  foreach term [$net getITerms] {
    if {[[$term getMTerm] getSigType] in {POWER GROUND}} {continue}
    if {[[$term getMTerm] getIoType] ne "INPUT"} {error "Internally driven input root"}
    lappend loads $term
  }
  if {![llength $loads]} {error "Unused input cannot be hidden by a receiver"}
  set rectangles {}
  foreach pin [$port getBPins] {foreach box [$pin getBoxes] {lappend rectangles $box}}
  if {[llength $rectangles]!=1} {error "Expected exactly one input landing"}
  set box [lindex $rectangles 0]
  if {[[$box getTechLayer] getName] ne "metal10"} {error "Expected M10 input landing"}
  set x [expr {([$box xMin]+[$box xMax])/2}]
  set y [expr {([$box yMin]+[$box yMax])/2}]
  set name feed_input_receiver_$feed_count
  if {[$feed_block findInst $name] ne "NULL"} {error "Duplicate input receiver"}
  set internal [odb::dbNet_create $feed_block ${name}_internal]
  if {$internal eq "NULL"} {error "Duplicate internal receiver net"}
  foreach term $loads {$term disconnect; $term connect $internal}
  set inst [odb::dbInst_create $feed_block $feed_master $name]
  $inst setLocation $x $y
  $inst setOrient R0
  $inst setPlacementStatus PLACED
  [$inst findITerm A] connect $net
  [$inst findITerm Z] connect $internal
  foreach term [$inst getITerms] {
    set kind [[$term getMTerm] getSigType]
    if {$kind in {POWER GROUND}} {
      set supply [expr {$kind eq "POWER" ? "VDD" : "VSS"}]
      set pg [$feed_block findNet $supply]
      if {$pg eq "NULL"} {error "Original supply absent"}
      $term connect $pg
    }
  }
  # PG connection precedes protection. This fixes a real receiver, not its load.
  set_dont_touch [get_cells $name]
  puts $feed_report "$name\t[$port getName]\t[$net getName]\t[$internal getName]\t[llength $loads]\t$x\t$y"
  incr feed_count
}
close $feed_report
if {$feed_count==0} {error "No fixed input receivers"}
global_connect
detailed_placement_helper
check_placement -verbose
# The following protection hook sees exactly the receiver input on each data
# root. Downstream fanout repair stays available on the new internal nets.

# Pre-freeze output stages for actual upper-interconnect loads. No clock,
# register, latency, numerical or protocol change. Fresh native RC and every
# original physical/function/LEC gate remain mandatory.
set driver_block [ord::get_db_block]
set driver_master [[ord::get_db] findMaster BUF_X32]
if {$driver_master eq "NULL"} {error "Missing actual BUF_X32"}
set driver_report [open $::env(RESULTS_DIR)/strong-output-drivers.tsv w]
set driver_count 0
set driver_sta_nets [dict create]
foreach net [get_nets *] {dict set driver_sta_nets [get_full_name $net] $net}
foreach port [$driver_block getBTerms] {
 if {[$port getSigType] in {POWER GROUND} || [$port getIoType] ne "OUTPUT"} {continue}
 set net [$port getNet]
 if {$net eq "NULL"} {error "Disconnected native output"}
 set shared_output [expr {[llength [$net getBTerms]]!=1}]
 if {$shared_output} {
  if {[$driver_block getName] ne "block_feed_s_macro"} {error "Ambiguous native output"}
  foreach peer [$net getBTerms] {if {[$peer getIoType] ne "OUTPUT"} {error "S alias is not exclusively outputs"}}
 }
 set terms {};set outputs 0
 foreach term [$net getITerms] {
  if {[[$term getMTerm] getSigType] in {POWER GROUND}} {continue}
  lappend terms $term
  if {[[$term getMTerm] getIoType] eq "OUTPUT"} {incr outputs}
 }
 if {$outputs!=1} {error "Native output must have one original driver"}
 set boxes {}
 foreach pin [$port getBPins] {foreach box [$pin getBoxes] {lappend boxes $box}}
 if {[llength $boxes]!=1} {error "Expected one M10 output landing"}
 set box [lindex $boxes 0]
 if {[[$box getTechLayer] getName] ne "metal10"} {error "Native output is not on M10"}
 set x [expr {([$box xMin]+[$box xMax])/2}];set y [expr {([$box yMin]+[$box yMax])/2}]
 set name control_output_driver_$driver_count
 if {[$driver_block findInst $name] ne "NULL"} {error "Output stage already inserted"}
 if {$shared_output} {
  # S a_bank/b_bank may be logical aliases. Each physical output still
  # receives its own stage; preserve the original driver and all consumers.
  set internal $net
  set net [odb::dbNet_create $driver_block ${name}_output]
  if {$net eq "NULL"} {error "Duplicate S output-stage net"}
  $port disconnect;$port connect $net
 } else {
  set internal [odb::dbNet_create $driver_block ${name}_internal]
  if {$internal eq "NULL"} {error "Duplicate output-stage net"}
  foreach term $terms {$term disconnect;$term connect $internal}
 }
 set inst [odb::dbInst_create $driver_block $driver_master $name]
 $inst setLocation $x $y
 $inst setOrient R0
 $inst setPlacementStatus PLACED
 [$inst findITerm A] connect $internal
 [$inst findITerm Z] connect $net
 foreach term [$inst getITerms] {
  set kind [[$term getMTerm] getSigType]
  if {$kind in {POWER GROUND}} {
   set supply [expr {$kind eq "POWER" ? "VDD" : "VSS"}];set pg [$driver_block findNet $supply]
   if {$pg eq "NULL"} {error "Missing original supply"}
   $term connect $pg
  }
 }
 set_dont_touch [get_cells $name]
 if {$shared_output} {
  set actual_net [get_nets [$net getName]]
  if {[llength $actual_net]!=1} {error "S alias output STA net missing"}
  set_dont_touch $actual_net
 } else {
  if {![dict exists $driver_sta_nets [$net getName]]} {error "Original output STA net missing"}
  set_dont_touch [dict get $driver_sta_nets [$net getName]]
 }
 puts $driver_report "$name\t[$port getName]\t[$internal getName]\t[$net getName]\t$x\t$y"
 incr driver_count
}
close $driver_report
if {$driver_count==0} {error "No actual output stages inserted"}
global_connect
detailed_placement_helper
check_placement -verbose

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
