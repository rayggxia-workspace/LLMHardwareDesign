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
  set relocations {};source $::env(PINXY_RELOCATIONS)
  set count 0
  foreach row $relocations {
    incr count;set pin [lindex $row 0]
    report_checks -through [get_ports $pin] -path_delay min_max -fields {capacitance slew fanout} -format full_clock_expanded -group_path_count 20 -digits 6 > $prefix.selected_$count.txt
  }
}

read_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/current_driver_sizing/r05/vector/routed.odb}
source {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_power_fix/r01/all75_verified_native_poses.tcl}
set b [ord::get_db_block]
fingerprint {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_power_fix/r01/before}
set fixes {};set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_power_fix/r01/actual9_orientation_fixes.tsv} w];puts $f "instance\tmaster\tx\ty\told_orientation\tnew_orientation"
foreach r $expected_poses {
 lassign $r name master x y orient status;set i [$b findInst $name]
 if {$i eq "NULL" || [[$i getMaster] getName] ne $master || [$i getLocation] ne [list $x $y] || [$i getPlacementStatus] ne $status} {error "Measured legal pose source differs in more than orientation"}
 if {[$i getOrient] ne $orient} {puts $f [join [list $name $master $x $y [$i getOrient] $orient] "\t"];lappend fixes [list $name $orient];$i setOrient $orient}
};close $f
if {[llength $fixes]!=9} {error "Not the measured nine-orientation replay defect"}
stage legal_pose_check {check_placement -verbose}

fingerprint {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_power_fix/r01/after}
write_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_power_fix/r01/orientation_corrected_NOT_SIGNAL_REROUTED.odb}
stage VDD {check_power_grid -net VDD -error_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_power_fix/r01/VDD.rpt}}
stage VSS {check_power_grid -net VSS -error_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_power_fix/r01/VSS.rpt}}
close $stages
