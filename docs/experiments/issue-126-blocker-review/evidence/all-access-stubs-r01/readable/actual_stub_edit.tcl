# Small matched pure-XY experiment. No resize, placement, CTS, filler removal,
# obstruction deletion, architecture change, or rule relaxation.
set out $::env(PINXY_OUTPUT)
set stages [open $out/actual_stub_edit.stages.tsv w]
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

read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_pin_retention/r01/routed.odb}
fingerprint {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/all_llsys_access_stubs/r01/before}
set b [ord::get_db_block];set tech [ord::get_db_tech];set original_obs [lsort [$b getObstructions]]
source {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/all_llsys_access_stubs/r01/actual_stub_specs.tcl}
if {![stage actual_all_selected_stubs_and_original_layer_pins {
 foreach spec $stub_specs {
  lassign $spec pin net layer points;set bt [$b findBTerm $pin]
  if {$bt eq "NULL" || [[$bt getNet] getName] ne $net} {error "Original bit peer changed"}
  set n [$bt getNet];set wire [$n getWire];if {$wire eq "NULL"} {error "Original routed conductor missing"}
  if {[$b findNet HPY_ACTUAL_ACCESS_STUB_STAGING] ne "NULL"} {error "Staging collision"}
  set temp [odb::dbNet_create $b HPY_ACTUAL_ACCESS_STUB_STAGING];set tw [odb::dbWire_create $temp];set enc [odb::dbWireEncoder]
  $enc begin $tw;$enc newPath [$tech findLayer $layer] ROUTED
  foreach point $points {lassign $point x y;$enc addPoint $x $y};$enc end;$wire append $tw;odb::dbNet_destroy $temp
  lassign [lindex $points end] x y;place_pin -pin_name $pin -layer $layer -location [list [expr {$x/2000.}] [expr {$y/2000.}]] -pin_size {.14 .14}
 }
}]} {close $stages;exit 1}
if {[lsort [$b getObstructions]] ne $original_obs} {error "Original block OBS changed"}

fingerprint {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/all_llsys_access_stubs/r01/after}
write_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/all_llsys_access_stubs/r01/routed.odb}
write_def {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/all_llsys_access_stubs/r01/routed.def}
stage VDD {check_power_grid -net VDD -error_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/all_llsys_access_stubs/r01/VDD.rpt}}
stage VSS {check_power_grid -net VSS -error_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/all_llsys_access_stubs/r01/VSS.rpt}}
source {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/drivers/deadline-all-access-stubs-r01/export_access.tcl}
close $stages
