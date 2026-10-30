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

read_liberty {/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib}
read_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/current_driver_sizing/r05/vector/routed.odb}
read_sdc {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/vec-physical-01/flow/results/nangate45/llhd_vec_original/base/6_final.sdc}
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set original_obs [lsort [$b getObstructions]];set temporary_obs {}
fingerprint {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/before}
set access_reservations {};source {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/inputs/trial-inputs-vector-access-r03/access_reservations.tcl}
foreach r $access_reservations {lassign $r ly a c d e;set z {};foreach v [list $a $c $d $e] {lappend z [expr {round($v*$u)}]};lappend temporary_obs [odb::dbObstruction_create $b [[ord::get_db_tech] findLayer $ly] {*}$z]}
set_routing_layers -signal metal2-metal10 -clock metal4-metal10
read_guides {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/current_driver_sizing/r05/vector/route.guide}
if {![stage begin_incremental {global_route -start_incremental}]} {close $stages;exit 1}
if {![stage restore_exact9_legal_poses {
set i [$b findInst {_457487_}];if {$i eq "NULL" || [[$i getMaster] getName] ne {AND3_X2} || [$i getOrient] ne {R0}} {error "Measured orientation source changed"};$i setOrient MX;$i setLocation 128820 1495200
set i [$b findInst {_464497_}];if {$i eq "NULL" || [[$i getMaster] getName] ne {NOR4_X4} || [$i getOrient] ne {R0}} {error "Measured orientation source changed"};$i setOrient MX;$i setLocation 2063780 834400
set i [$b findInst {_484454_}];if {$i eq "NULL" || [[$i getMaster] getName] ne {OAI22_X2} || [$i getOrient] ne {MX}} {error "Measured orientation source changed"};$i setOrient R0;$i setLocation 1089840 501200
set i [$b findInst {output1406}];if {$i eq "NULL" || [[$i getMaster] getName] ne {BUF_X2} || [$i getOrient] ne {R0}} {error "Measured orientation source changed"};$i setOrient MX;$i setLocation 2292920 1344000
set i [$b findInst {output1284}];if {$i eq "NULL" || [[$i getMaster] getName] ne {BUF_X2} || [$i getOrient] ne {R0}} {error "Measured orientation source changed"};$i setOrient MX;$i setLocation 2292160 1310400
set i [$b findInst {wr_data_r\[34\]$_DFFE_PN0P_}];if {$i eq "NULL" || [[$i getMaster] getName] ne {DFFR_X2} || [$i getOrient] ne {MX}} {error "Measured orientation source changed"};$i setOrient R0;$i setLocation 1347860 1223600
set i [$b findInst {wr_data_r\[36\]$_DFFE_PN0P_}];if {$i eq "NULL" || [[$i getMaster] getName] ne {DFFR_X2} || [$i getOrient] ne {MX}} {error "Measured orientation source changed"};$i setOrient R0;$i setLocation 1355840 1195600
set i [$b findInst {wr_data_r\[42\]$_DFFE_PN0P_}];if {$i eq "NULL" || [[$i getMaster] getName] ne {DFFR_X2} || [$i getOrient] ne {R0}} {error "Measured orientation source changed"};$i setOrient MX;$i setLocation 1370280 1248800
set i [$b findInst {place152232}];if {$i eq "NULL" || [[$i getMaster] getName] ne {BUF_X2} || [$i getOrient] ne {R0}} {error "Measured orientation source changed"};$i setOrient MX;$i setLocation 1543180 571200
check_placement -verbose}]} {close $stages;exit 1}
if {![stage incremental_global_route {global_route -end_incremental -guide_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/route.guide} -congestion_report_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/congestion.rpt}}]} {close $stages;exit 1}
set selected_names {{_061350_} {_061356_} {_061358_} {_129978_} {_129979_} {_129980_} {_136262_} {_136279_} {_136281_} {_136282_} {_155357_} {_156103_} {_156104_} {_194673_} {_211990_} {_211992_} {_211998_} {clknet_leaf_167_clk} {clknet_leaf_172_clk} {net101598} {net1282} {net147059} {net150360} {net152214} {net157536} {net92129} {net98578} {vec_wr_wdata[208]} {vec_wr_wdata[88]} {wr_data_r\[34\]} {wr_data_r\[36\]} {wr_data_r\[42\]}};set_nets_to_route $selected_names
if {![stage incident_nets_detailed_route {detailed_route -output_drc {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/route.drc} -verbose 1}]} {catch {write_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/failed_route.odb}};close $stages;exit 1}
foreach ob $temporary_obs {odb::dbObstruction_destroy $ob};if {[lsort [$b getObstructions]] ne $original_obs} {error "Original OBS changed"}
fingerprint {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/after}
write_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/routed.odb}
write_def {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/routed.def}
stage VDD {check_power_grid -net VDD -error_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/VDD.rpt}}
stage VSS {check_power_grid -net VSS -error_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/VSS.rpt}}
source {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/drivers/deadline-vector-pose-route-r01/export_access.tcl}
stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/extracted.spef};read_spef {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/extracted.spef}}
stage sta {report_worst_slack -max -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/setup.txt};report_worst_slack -min -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/hold.txt};report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/checks.txt};check_setup -verbose > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/constraint_coverage.txt};report_parasitic_annotation -report_unannotated > {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_pose_route_fix/r01/parasitic_coverage.txt}}
close $stages
