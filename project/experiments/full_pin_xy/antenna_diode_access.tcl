# Actual library diode ECO. No deletion/relaxation of antenna or placement rules.
# The Python driver prepends the unchanged stage/fingerprint helpers and libraries.
proc original_functional_contract {file} {
  set f [open $file w]
  foreach i [[ord::get_db_block] getInsts] {
    if {[[$i getMaster] getType] eq "CORE_SPACER" || [string match ${::pinxy_diode_prefix}* [$i getName]]} {continue}
    puts $f [list CELL [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus]]
    foreach t [$i getITerms] {
      set n [$t getNet];set nn NULL;if {$n ne "NULL"} {set nn [$n getName]}
      puts $f [list TERM [$i getName] [[$t getMTerm] getName] [$t getIoType] [$t getSigType] $nn]
    }
  };close $f
}
proc obstruction_contract {} {
  set rows {}
  foreach ob [[ord::get_db_block] getObstructions] {
    set r [$ob getBBox]
    lappend rows [list [$ob getId] [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
  };return [lsort $rows]
}
set pinxy_diode_prefix PINXY_ANT_
set pinxy_diode_count 636
if {[info exists ::env(PINXY_DIODE_PREFIX)]} {set pinxy_diode_prefix $::env(PINXY_DIODE_PREFIX)}
if {[info exists ::env(PINXY_DIODE_COUNT)]} {set pinxy_diode_count $::env(PINXY_DIODE_COUNT)}
read_db $::env(PINXY_DIODE_SOURCE)
read_sdc $::env(PINXY_DIODE_SDC)
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron]
set dm [[ord::get_db] findMaster ANTENNA_X1]
if {$dm eq "NULL" || [$dm getType] ne "CORE_ANTENNACELL"} {error "Missing real ANTENNA_X1 master/type"}
set a [$dm findMTerm A]
if {$a eq "NULL" || [$a getIoType] ne "INPUT"} {error "Actual diode A is not an input"}
foreach mt [$dm getMTerms] {
  if {[$mt getSigType] ni {POWER GROUND} && ([$mt getName] ne "A" || [$mt getIoType] ne "INPUT")} {error "Unexpected diode signal terminal"}
}
foreach i [$b getInsts] {if {[string match ${pinxy_diode_prefix}* [$i getName]]} {error "Source already contains this ECO prefix"}}
fingerprint $out/before
original_functional_contract $out/before.original.tsv
set original_obs [obstruction_contract]
set filler_masters {};set original_status {}
foreach i [$b getInsts] {
  set m [$i getMaster]
  if {[$m getType] eq "CORE_SPACER"} {lappend filler_masters [$m getName];continue}
  lappend original_status [list $i [$i getPlacementStatus]]
}
set filler_masters [lsort -unique $filler_masters]
if {![llength $filler_masters]} {error "Missing original filler master set"}
set temporary_obs {};set access_reservations {};source $::env(PINXY_DIODE_RESERVATIONS)
foreach row $access_reservations {
  lassign $row ly x0 y0 x1 y1;set coords {}
  foreach v [list $x0 $y0 $x1 $y1] {lappend coords [expr {round($v*$u)}]}
  lappend temporary_obs [odb::dbObstruction_create $b [[ord::get_db_tech] findLayer $ly] {*}$coords]
}
set_routing_layers -signal metal2-metal10 -clock metal4-metal10
if {[info exists ::env(PINXY_DIODE_GUIDES)]} {
  read_guides $::env(PINXY_DIODE_GUIDES)
  if {![stage begin_incremental_GRT {global_route -start_incremental}]} {close $stages;exit 1}
}
if {![stage actual_diode_insert {
  remove_fillers
  # Freeze all old functional cells for this ECO's legalizer, then restore status.
  foreach row $original_status {lassign $row i status;if {$status ni {LOCKED FIRM COVER}} {$i setPlacementStatus FIRM}}
  set requested_nets {};source $::env(PINXY_DIODE_REQUESTS)
  set f [open $out/diode_receivers.tsv w]
  puts $f "diode\tnet\treceiver_instance\treceiver_pin\treceiver_bbox_dbu\tinitial_x_dbu\tinitial_y_dbu\tmaster"
  set count 0;set diode_cells {}
  foreach row $requested_nets {
    lassign $row name cx cy
    set n [$b findNet $name]
    if {$n eq "NULL" || [$n getSigType] in {POWER GROUND}} {error "Missing actual signal net $name"}
    set best {};set best_distance Inf
    foreach t [$n getITerms] {
      if {[$t getIoType] ne "INPUT" || [$t getSigType] in {POWER GROUND}} {continue}
      set i [$t getInst];set bb [$i getBBox]
      set x [expr {([$bb xMin]+[$bb xMax])/2.0}];set y [expr {([$bb yMin]+[$bb yMax])/2.0}]
      set distance [expr {abs($x-$cx)+abs($y-$cy)}]
      if {$distance<$best_distance} {set best $t;set best_distance $distance}
    }
    if {$best eq ""} {error "No verified receiver for $name; do not invent one"}
    set receiver [$best getInst];set bb [$receiver getBBox]
    set x [$bb xMax];set y [$bb yMin]
    set inst [odb::dbInst_create $b $dm [format ${pinxy_diode_prefix}%04d $count]]
    if {$inst eq "NULL"} {error "Cannot create actual diode"}
    $inst setLocation $x $y;$inst setPlacementStatus PLACED
    [$inst findITerm A] connect $n
    lappend diode_cells $inst
    puts $f [join [list [$inst getName] $name [$receiver getName] [[$best getMTerm] getName] [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]] $x $y [$dm getName]] "\t"]
    incr count
  };close $f
  if {$count!=$pinxy_diode_count} {error "Unexpected count $count"}
  write_db $out/inserted_NOT_LEGALIZED_OR_ROUTED.odb
}]} {close $stages;exit 1}
if {![stage diode_legalization {
  detailed_placement -use_diamond_legalizer
  check_placement -verbose
  foreach row $original_status {lassign $row i status;$i setPlacementStatus $status}
  original_functional_contract $out/placed.original.tsv
  set f [open $out/before.original.tsv r];set old [read $f];close $f
  set f [open $out/placed.original.tsv r];set current [read $f];close $f
  if {$old ne $current} {error "Original cell pose/master/terminal relation changed"}
  filler_placement -prefix ${pinxy_diode_prefix}FILL_ $filler_masters
  set diode_pattern [format {^%s[0-9]+$} $pinxy_diode_prefix]
  add_global_connection -net VDD -inst_pattern $diode_pattern -pin_pattern {^VDD$} -power
  add_global_connection -net VSS -inst_pattern $diode_pattern -pin_pattern {^VSS$} -ground
  global_connect
  check_placement -verbose
  set f [open $out/diode_placed.tsv w];puts $f "diode\tnet\tx_dbu\ty_dbu\torientation\twidth_dbu\theight_dbu\tVDD\tVSS"
  foreach i $diode_cells {
    set n [[$i findITerm A] getNet];set vp [[$i findITerm VDD] getNet];set vg [[$i findITerm VSS] getNet]
    if {$vp eq "NULL" || $vg eq "NULL" || [$vp getName] ne "VDD" || [$vg getName] ne "VSS"} {error "Diode PG not connected"}
    lassign [$i getLocation] x y
    puts $f [join [list [$i getName] [$n getName] $x $y [$i getOrient] [$dm getWidth] [$dm getHeight] [$vp getName] [$vg getName]] "\t"]
  };close $f
  write_db $out/placed_NOT_ROUTED.odb
}]} {close $stages;exit 1}
if {[info exists ::env(PINXY_DIODE_GUIDES)]} {
  if {![stage global_route {global_route -end_incremental -guide_file $out/route.guide -congestion_report_file $out/congestion.rpt}]} {close $stages;exit 1}
} else {
  if {![stage full_signal_clock_rip {
    foreach n [$b getNets] {if {[$n getSigType] ni {POWER GROUND}} {set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w}}}
  }]} {close $stages;exit 1}
  if {![stage global_route {global_route -guide_file $out/route.guide -congestion_report_file $out/congestion.rpt}]} {close $stages;exit 1}
}
if {![stage detailed_route {detailed_route -output_drc $out/route.drc -verbose 1}]} {close $stages;exit 1}
if {![stage preserve_original_views {
  foreach ob $temporary_obs {odb::dbObstruction_destroy $ob}
  write_db $out/routed_PENDING_CONTRACTS.odb
  if {[obstruction_contract] ne $original_obs} {error "Original OBS changed"}
  original_functional_contract $out/after.original.tsv
  fingerprint $out/after
  set f [open $out/before.original.tsv r];set old [read $f];close $f
  set f [open $out/after.original.tsv r];set current [read $f];close $f
  if {$old ne $current} {error "Original cell/endpoint contract changed"}
  write_db $out/routed.odb
  write_def $out/routed.def
  write_verilog $out/mapped.v
}]} {close $stages;exit 1}
report_wire_length -detailed_route -summary -file $out/wire_length.csv
stage VDD {check_power_grid -net VDD -error_file $out/VDD.rpt}
stage VSS {check_power_grid -net VSS -error_file $out/VSS.rpt}
stage whole_signal_geometry {source $::env(PINXY_DIODE_EXPORT_ACCESS)}
stage rcx {
  define_process_corner -ext_model_index 0 X
  set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules
  extract_parasitics;write_spef $out/extracted.spef;read_spef $out/extracted.spef
}
stage sta {
  report_worst_slack -max -digits 6 > $out/setup.txt
  report_worst_slack -min -digits 6 > $out/hold.txt
  report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > $out/checks.txt
  check_setup -verbose > $out/constraint_coverage.txt
  report_parasitic_annotation -report_unannotated > $out/parasitic_coverage.txt
}
close $stages
