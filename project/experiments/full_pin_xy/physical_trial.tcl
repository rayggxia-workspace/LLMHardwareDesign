# Small matched pure-XY experiment. No resize, placement, CTS, filler removal,
# obstruction deletion, architecture change, or rule relaxation.
set out $::env(PINXY_OUTPUT)
set stages [open $out/stages.tsv w]
puts $stages "stage\tstatus\tdetail"
proc stage {name body} {
  global stages
  puts "STAGE_START $name"
  if {[catch {uplevel 1 $body} result options]} {
    puts $stages "$name\tFAIL\t[string map [list \n { | } \t { }] $result]";flush $stages
    puts "STAGE_FAIL $name $result"
    set f [open "$::env(PINXY_OUTPUT)/$name.error.txt" w];puts $f [dict get $options -errorinfo];close $f
    return 0
  }
  puts $stages "$name\tEXECUTED\t";flush $stages
  puts "STAGE_EXECUTED $name"
  return 1
}
proc fingerprint {prefix} {
  set b [ord::get_db_block]
  set f [open "$prefix.cells.tsv" w]
  foreach i [$b getInsts] {
    puts $f [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus]]
    foreach t [$i getITerms] {set n [$t getNet];set nn NULL;if {$n ne "NULL"} {set nn [$n getName]};puts $f [list [$i getName] [[$t getMTerm] getName] $nn]}
  };close $f
  set f [open "$prefix.pins.tsv" w]
  foreach t [$b getBTerms] {
    set n [$t getNet];set nn NULL;if {$n ne "NULL"} {set nn [$n getName]}
    foreach p [$t getBPins] {foreach r [$p getBoxes] {puts $f [list [$t getName] [$t getIoType] [$t getSigType] $nn [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]]}}
  };close $f
  set f [open "$prefix.pdn.tsv" w]
  foreach n [$b getNets] {foreach sw [$n getSWires] {foreach r [$sw getWires] {puts $f [list [$n getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax] [$r isVia]]}}};close $f
  set f [open "$prefix.die.tsv" w];set d [$b getDieArea];puts $f [list [$d xMin] [$d yMin] [$d xMax] [$d yMax]];close $f
}
proc timing {prefix} {
  report_worst_slack -max -digits 6 > $prefix.setup.txt
  report_worst_slack -min -digits 6 > $prefix.hold.txt
  report_tns -max -digits 6 > $prefix.setup_tns.txt
  report_tns -min -digits 6 > $prefix.hold_tns.txt
  report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > $prefix.checks.txt
  report_checks -path_delay min_max -group_path_count 1000000 -endpoint_path_count 1 -format json > $prefix.paths.json
  check_setup -verbose > $prefix.constraint_coverage.txt
  report_parasitic_annotation -report_unannotated > $prefix.parasitic_coverage.txt
}
if {![stage load {
  source $::env(PINXY_LIBS_TCL)
  read_db $::env(PINXY_ODB)
  read_sdc $::env(PINXY_SDC)
  source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
  fingerprint $out/before
}]} {close $stages;exit 1}
if {$::env(PINXY_PLAN) eq "A"} {
  stage baseline_rc {
    define_process_corner -ext_model_index 0 X
    set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules
    extract_parasitics
    write_spef $out/extracted.spef
    read_spef $out/extracted.spef
  }
} else {
  if {![stage move {
    set relocations {};source $::env(PINXY_RELOCATIONS)
    set block [ord::get_db_block];set units [$block getDbUnitsPerMicron];set changednets {}
    foreach r $relocations {
      lassign $r name layer x y width height
      set term [$block findBTerm $name];if {$term eq "NULL"} {error "Missing pin $name"}
      set oldboxes {};foreach p [$term getBPins] {foreach box [$p getBoxes] {lappend oldboxes $box}}
      if {[llength $oldboxes]!=1} {error "Expected one pin box $name"}
      set box [lindex $oldboxes 0]
      if {[[$box getTechLayer] getName] ne $layer} {error "Layer mismatch $name"}
      if {abs(([$box xMax]-[$box xMin])/double($units)-$width)>1e-8 || abs(([$box yMax]-[$box yMin])/double($units)-$height)>1e-8} {error "Size mismatch $name"}
      place_pin -pin_name $name -layer $layer -location [list $x $y] -pin_size [list $width $height]
      set boxes {};foreach p [$term getBPins] {foreach box [$p getBoxes] {lappend boxes $box}}
      if {[llength $boxes]!=1} {error "Unexpected new box count $name"}
      set box [lindex $boxes 0]
      if {[[$box getTechLayer] getName] ne $layer || abs(([$box xMin]+[$box xMax])/(2.0*$units)-$x)>0.000001 || abs(([$box yMin]+[$box yMax])/(2.0*$units)-$y)>0.000001} {error "place_pin clamped or snapped $name"}
      lappend changednets [$term getNet]
    }
    fingerprint $out/moved
    write_db $out/moved.odb
    # Rip up only nets incident on selected pins; preserve all other existing routes as input.
    foreach n [lsort -unique $changednets] {set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w}}
    write_db $out/ripped.odb
  }]} {close $stages;exit 1}
  set routed [stage global_route {
    set_routing_layers -signal metal2-metal$::env(PINXY_TOP_LAYER) -clock metal4-metal$::env(PINXY_TOP_LAYER)
    global_route -guide_file $out/route.guide -congestion_report_file $out/congestion.rpt
    write_db $out/global.odb
  }]
  if {$routed} {set routed [stage detailed_route {
    detailed_route -output_drc $out/route.drc -output_maze $out/maze.log -verbose 1
    write_db $out/routed.odb
  }]}
  if {!$routed} {stage failed_route_checkpoint {write_db $out/failed-route.odb};close $stages;exit 1}
  stage extract_rc {
    define_process_corner -ext_model_index 0 X
    set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules
    extract_parasitics
    write_spef $out/extracted.spef
    read_spef $out/extracted.spef
  }
}
stage fresh_native_drc {drt::check_drc -output_file $out/fresh_route.drc}
stage odb_route_connectivity {
  odb::orderWires [ord::get_db_block] true
  set f [open $out/odb_connectivity.tsv w];puts $f "net\titerms\tbterms\tisConnected\tisRCDisconnected"
  foreach n [[ord::get_db_block] getNets] {
    if {[$n getSigType] in {POWER GROUND}} {continue}
    puts $f [join [list [$n getName] [llength [$n getITerms]] [llength [$n getBTerms]] [$n isConnected] [$n isRCDisconnected]] "\t"]
  };close $f
}
stage placement {check_placement -verbose}
foreach net {VDD VSS} {stage pdn_$net {check_power_grid -net $net -error_file $out/$net.pdn.rpt}}
stage wire_statistics {report_wire_length -detailed_route -summary -file $out/wire_length.csv}
stage sta {timing $out/timing}
stage abstract {write_abstract_lef $out/abstract.lef}
stage final {fingerprint $out/after;write_db $out/checked.odb;write_def $out/checked.def;write_verilog $out/checked.v;write_sdc $out/checked.sdc}
close $stages
puts "TRIAL_STAGES_FINISHED_SEE_SEPARATE_GATES"
