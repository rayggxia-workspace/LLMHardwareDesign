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

read_lef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/upper_layer_probe/r01/model/research12.tech.lef}
read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef
read_verilog {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/partial_fixed_upper_probe/r01/fixture.v}
link_design hpy_partial_fixed
initialize_floorplan -die_area {0 0 64 64} -core_area {1 1 63 63} -site FreePDK45_38x28_10R_NP_162NW_34O
make_tracks
set b [ord::get_db_block];set tech [ord::get_db_tech]
place_pin -pin_name src -layer metal10 -location {9.695 16.07} -pin_size {.8 .8}
place_pin -pin_name pad_a -layer metal10 -location {25.695 16.07} -pin_size {.8 .8}
place_pin -pin_name pad_b -layer metal10 -location {25.695 48.07} -pin_size {.8 .8}
place_pin -pin_name dst -layer metal10 -location {41.695 48.07} -pin_size {.8 .8}
set n [[$b findBTerm src] getNet];if {[llength [$n getBTerms]]!=4 || [llength [$b getNets]]!=1} {error "Native four-terminal net aliasing failed"}
set m10 [$tech findLayer metal10];if {[$m10 getWidth]!=1600} {error "Actual M10 width is not0.8um"};set w [odb::dbWire_create $n];set e [odb::dbWireEncoder];$e begin $w;$e newPath $m10 FIXED;$e addPoint 51390 32140;$e addPoint 51390 96140;$e end
set ::env(PINXY_ACCESS_OUT) {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/partial_fixed_upper_probe/r01/FIXED/before.tsv}
source {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/drivers/deadline-partial-fixed-upper-r01/export_access.tcl}
write_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/partial_fixed_upper_probe/r01/FIXED/before_NOT_SYSTEM.odb}
write_def {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/partial_fixed_upper_probe/r01/FIXED/before.def}
set_routing_layers -signal metal11-metal12 -clock metal11-metal12
if {![stage native_global {global_route -guide_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/partial_fixed_upper_probe/r01/FIXED/route.guide} -congestion_report_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/partial_fixed_upper_probe/r01/FIXED/congestion.rpt}}]} {close $stages;exit 1}
if {![stage native_upper_route {detailed_route -output_drc {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/partial_fixed_upper_probe/r01/FIXED/route.drc} -verbose 1}]} {close $stages;exit 1}
write_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/partial_fixed_upper_probe/r01/FIXED/routed_NOT_SYSTEM.odb}
write_def {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/partial_fixed_upper_probe/r01/FIXED/routed.def}
set ::env(PINXY_ACCESS_OUT) {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/partial_fixed_upper_probe/r01/FIXED/after.tsv}
source {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/drivers/deadline-partial-fixed-upper-r01/export_access.tcl}
stage independent_native_DRC {drt::check_drc -output_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/partial_fixed_upper_probe/r01/FIXED/independent.drc}}
close $stages
