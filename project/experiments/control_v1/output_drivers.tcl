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
 if {$net eq "NULL" || [llength [$net getBTerms]]!=1} {error "Ambiguous native output"}
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
 set internal [odb::dbNet_create $driver_block ${name}_internal]
 if {$internal eq "NULL"} {error "Duplicate output-stage net"}
 foreach term $terms {$term disconnect;$term connect $internal}
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
 if {![dict exists $driver_sta_nets [$net getName]]} {error "Original output STA net missing"}
 set_dont_touch [dict get $driver_sta_nets [$net getName]]
 puts $driver_report "$name\t[$port getName]\t[$internal getName]\t[$net getName]\t$x\t$y"
 incr driver_count
}
close $driver_report
if {$driver_count==0} {error "No actual output stages inserted"}
global_connect
detailed_placement_helper
check_placement -verbose
