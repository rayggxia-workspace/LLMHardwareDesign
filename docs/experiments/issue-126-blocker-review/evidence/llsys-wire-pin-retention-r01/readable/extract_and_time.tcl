# Small matched pure-XY experiment. No resize, placement, CTS, filler removal,
# obstruction deletion, architecture change, or rule relaxation.
set out $::env(PINXY_OUTPUT)
set stages [open $out/RC_STA_stages.tsv w]
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
  set relocations {};source $::env(PINXY_RELOCATIONS)
  set count 0
  foreach row $relocations {
    incr count;set pin [lindex $row 0]
    report_checks -through [get_ports $pin] -path_delay min_max -fields {capacitance slew fanout} -format full_clock_expanded -group_path_count 20 -digits 6 > $prefix.selected_$count.txt
  }
}

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

read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_pin_retention/r01/routed.odb}
read_sdc {/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/auxiliary-route-llaccel-abc-logic-4c-01/flow/results/nangate45/hpy_llaccel_aux/base/5_1_grt.sdc}
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
set_routing_layers -signal metal2-metal8 -clock metal4-metal8
stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_pin_retention/r01/extracted.spef};read_spef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_pin_retention/r01/extracted.spef}}
stage sta {report_worst_slack -max -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_pin_retention/r01/setup.txt};report_worst_slack -min -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_pin_retention/r01/hold.txt};report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_pin_retention/r01/checks.txt};check_setup -verbose > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_pin_retention/r01/constraint_coverage.txt};report_parasitic_annotation -report_unannotated > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_pin_retention/r01/parasitic_coverage.txt}}
close $stages
