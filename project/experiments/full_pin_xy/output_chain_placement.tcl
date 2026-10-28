# Move existing proven identity buffers on private output chains only.
# No net split, new buffer, master swap, protocol change or timing exception.
proc net_drivers_sinks {net} {
  set drivers {};set sinks {};set unsupported 0
  foreach t [$net getITerms] {
    if {[$t getSigType] in {POWER GROUND}} {continue}
    switch [$t getIoType] {OUTPUT {lappend drivers $t} INPUT {lappend sinks $t} default {set unsupported 1}}
  }
  return [list $drivers $sinks $unsupported]
}
proc connection_contract {file} {
  set f [open $file w]
  foreach i [[ord::get_db_block] getInsts] {
    if {[[$i getMaster] getType] eq "CORE_SPACER"} {continue}
    puts $f [list CELL [$i getName] [[$i getMaster] getName]]
    foreach t [$i getITerms] {
      set n [$t getNet];set name NULL;if {$n ne "NULL"} {set name [$n getName]}
      puts $f [list TERM [$i getName] [[$t getMTerm] getName] [$t getIoType] [$t getSigType] $name]
    }
  };close $f
}
proc nonselected_pose_contract {file} {
  set f [open $file w]
  foreach i [[ord::get_db_block] getInsts] {
    if {[[$i getMaster] getType] eq "CORE_SPACER" || [dict exists $::selected_buffers [$i getName]]} {continue}
    puts $f [list [$i getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus]]
  };close $f
}
proc obs_snapshot {} {
  set result {}
  foreach ob [[ord::get_db_block] getObstructions] {set bb [$ob getBBox];lappend result [list [$ob getId] [[$bb getTechLayer] getName] [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]}
  return [lsort $result]
}
read_db $::env(PINXY_CHAIN_SOURCE)
read_sdc $::env(PINXY_CHAIN_SDC)
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
source $::env(PINXY_CHAIN_MODELS)
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set selected_buffers [dict create];set chains {}
set f [open $out/output_selection.tsv w];puts $f "port\tstatus\tdriver_bbox_center_to_port_L1_um\tprivate_buffer_count"
foreach port [$b getBTerms] {
  if {[$port getIoType] ne "OUTPUT" || [$port getSigType] in {POWER GROUND CLOCK}} {continue}
  set boxes {};foreach bp [$port getBPins] {foreach r [$bp getBoxes] {lappend boxes $r}}
  if {[llength $boxes]!=1} {puts $f [join [list [$port getName] PRESERVED_UNSUPPORTED_PIN_RECTANGLE_COUNT {} 0] "\t"];continue}
  set box [lindex $boxes 0];set px [expr {([$box xMin]+[$box xMax])/2.0}];set py [expr {([$box yMin]+[$box yMax])/2.0}]
  set n [$port getNet];if {$n eq "NULL"} {puts $f [join [list [$port getName] PRESERVED_UNCONNECTED {} 0] "\t"];continue}
  lassign [net_drivers_sinks $n] drivers sinks unknown
  if {$unknown || [llength $drivers]!=1 || [llength $sinks]!=0 || [llength [$n getBTerms]]!=1} {puts $f [join [list [$port getName] PRESERVED_SHARED_OR_NONUNIQUE_OUTPUT {} 0] "\t"];continue}
  set bb [[[lindex $drivers 0] getInst] getBBox]
  set distance [expr {(abs(([$bb xMin]+[$bb xMax])/2.0-$px)+abs(([$bb yMin]+[$bb yMax])/2.0-$py))/$u}]
  if {$distance<100} {puts $f [join [list [$port getName] PRESERVED_DRIVER_WITHIN_100UM $distance 0] "\t"];continue}
  set chain {};set current $n;set downstream NULL
  set anchor_x [expr {([$bb xMin]+[$bb xMax])/2.0}];set anchor_y [expr {([$bb yMin]+[$bb yMax])/2.0}]
  for {set depth 0} {$depth<8} {incr depth} {
    if {[$current getSigType] in {POWER GROUND CLOCK}} {break}
    lassign [net_drivers_sinks $current] drivers sinks unknown
    if {$unknown || [llength $drivers]!=1} {break}
    if {$depth>0 && ([llength $sinks]!=1 || [lindex $sinks 0] ne $downstream || [llength [$current getBTerms]]!=0)} {break}
    set ot [lindex $drivers 0];set inst [$ot getInst];set master [[$inst getMaster] getName]
    set bb [$inst getBBox];set anchor_x [expr {([$bb xMin]+[$bb xMax])/2.0}];set anchor_y [expr {([$bb yMin]+[$bb yMax])/2.0}]
    if {[$inst getPlacementStatus] in {LOCKED FIRM COVER}} {break}
    if {![dict exists $buffer_models $master] || [dict exists $selected_buffers [$inst getName]]} {break}
    lassign [dict get $buffer_models $master] ip op
    if {[[$ot getMTerm] getName] ne $op} {break}
    set it [$inst findITerm $ip];set upstream [$it getNet]
    if {$upstream eq "NULL"} {break}
    lappend chain $inst
    set current $upstream;set downstream $it
  }
  if {![llength $chain]} {puts $f [join [list [$port getName] PRESERVED_NO_PROVEN_PRIVATE_IDENTITY_BUFFER $distance 0] "\t"];continue}
  # Locate the retained upstream physical driver, including a shared branch.
  lassign [net_drivers_sinks $current] upstream_drivers upstream_sinks unknown
  if {!$unknown && [llength $upstream_drivers]==1} {
    set bb [[[lindex $upstream_drivers 0] getInst] getBBox]
    set anchor_x [expr {([$bb xMin]+[$bb xMax])/2.0}];set anchor_y [expr {([$bb yMin]+[$bb yMax])/2.0}]
  }
  foreach i $chain {dict set selected_buffers [$i getName] $i}
  lappend chains [list [$port getName] $chain $px $py $anchor_x $anchor_y]
  puts $f [join [list [$port getName] PROPOSED_EXISTING_PRIVATE_CHAIN_RELOCATION $distance [llength $chain]] "\t"]
};close $f
if {![dict size $selected_buffers]} {error "No supported real output-chain relocation; do not reroute unchanged design"}
fingerprint $out/before
connection_contract $out/before.connections.tsv
nonselected_pose_contract $out/before.nonselected.tsv
set original_obs [obs_snapshot];set original_status {};set filler_masters {}
foreach i [$b getInsts] {
  if {[[$i getMaster] getType] eq "CORE_SPACER"} {lappend filler_masters [[$i getMaster] getName];continue}
  lappend original_status [list $i [$i getPlacementStatus]]
}
set filler_masters [lsort -unique $filler_masters]
if {![stage existing_buffer_relocation {
  remove_fillers
  foreach row $original_status {
    lassign $row i status
    if {[dict exists $selected_buffers [$i getName]]} {$i setPlacementStatus PLACED} elseif {$status ni {LOCKED FIRM COVER}} {$i setPlacementStatus FIRM}
  }
  set f [open $out/proposed_existing_buffer_moves.tsv w];puts $f "port\tinstance\tmaster\told_x_dbu\told_y_dbu\tproposed_x_dbu\tproposed_y_dbu"
  foreach row $chains {
    lassign $row port chain px py ax ay;set count [llength $chain];set j 0
    foreach i $chain {
      set fraction [expr {double([incr j])/($count+1)}]
      set x [expr {round($px+($ax-$px)*$fraction)}];set y [expr {round($py+($ay-$py)*$fraction)}]
      lassign [$i getLocation] ox oy
      puts $f [join [list $port [$i getName] [[$i getMaster] getName] $ox $oy $x $y] "\t"]
      $i setLocation $x $y
    }
  };close $f
  write_db $out/moved_NOT_LEGALIZED_OR_ROUTED.odb
}]} {close $stages;exit 1}
if {![stage legalization {
  detailed_placement -use_diamond_legalizer;check_placement -verbose
  foreach row $original_status {lassign $row i status;$i setPlacementStatus $status}
  if {[llength $filler_masters]} {filler_placement -prefix PINXY_CHAIN_FILL_ $filler_masters} else {puts "ORIGINAL_HAS_NO_CORE_SPACERS_NONE_ADDED"}
  global_connect;check_placement -verbose
  nonselected_pose_contract $out/placed.nonselected.tsv
  set f [open $out/before.nonselected.tsv r];set old [read $f];close $f
  set f [open $out/placed.nonselected.tsv r];set current [read $f];close $f
  if {$old ne $current} {error "Nonselected instance pose changed"}
  write_db $out/placed_NOT_ROUTED.odb
}]} {close $stages;exit 1}
set temporary_obs {};set access_reservations {};source $::env(PINXY_CHAIN_RESERVATIONS)
foreach row $access_reservations {
  lassign $row ly x0 y0 x1 y1;set coords {};foreach v [list $x0 $y0 $x1 $y1] {lappend coords [expr {round($v*$u)}]}
  lappend temporary_obs [odb::dbObstruction_create $b [[ord::get_db_tech] findLayer $ly] {*}$coords]
}
set_routing_layers -signal metal2-metal8 -clock metal4-metal8
foreach n [$b getNets] {if {[$n getSigType] ni {POWER GROUND}} {set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w}}}
if {![stage global_route {global_route -guide_file $out/route.guide -congestion_report_file $out/congestion.rpt}]} {close $stages;exit 1}
if {![stage detailed_route {detailed_route -output_drc $out/route.drc -verbose 1}]} {close $stages;exit 1}
if {![stage preserve_contracts {
  foreach ob $temporary_obs {odb::dbObstruction_destroy $ob}
  if {[obs_snapshot] ne $original_obs} {error "Original OBS changed"}
  connection_contract $out/after.connections.tsv
  nonselected_pose_contract $out/after.nonselected.tsv
  fingerprint $out/after
  foreach kind {connections nonselected} {
    set f [open $out/before.$kind.tsv r];set a [read $f];close $f
    set f [open $out/after.$kind.tsv r];set z [read $f];close $f
    if {$a ne $z} {error "Original functional or nonselected contract changed"}
  }
  set f [open $out/actual_existing_buffer_moves.tsv w];puts $f "instance\tmaster\tx_dbu\ty_dbu\torientation"
  dict for {name i} $selected_buffers {lassign [$i getLocation] x y;puts $f [join [list $name [[$i getMaster] getName] $x $y [$i getOrient]] "\t"]};close $f
  write_db $out/routed.odb;write_def $out/routed.def;write_verilog $out/mapped.v
}]} {close $stages;exit 1}
report_wire_length -detailed_route -summary -file $out/wire_length.csv
stage VDD {check_power_grid -net VDD -error_file $out/VDD.rpt}
stage VSS {check_power_grid -net VSS -error_file $out/VSS.rpt}
stage whole_signal_geometry {source $::env(PINXY_CHAIN_EXPORT_ACCESS)}
stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef $out/extracted.spef;read_spef $out/extracted.spef}
stage sta {
  report_worst_slack -max -digits 6 > $out/setup.txt
  report_worst_slack -min -digits 6 > $out/hold.txt
  report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > $out/checks.txt
  check_setup -verbose > $out/constraint_coverage.txt
  report_parasitic_annotation -report_unannotated > $out/parasitic_coverage.txt
}
close $stages
