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
