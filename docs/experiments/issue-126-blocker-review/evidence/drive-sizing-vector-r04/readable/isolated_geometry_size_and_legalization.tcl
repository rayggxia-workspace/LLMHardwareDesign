# Small matched pure-XY experiment. No resize, placement, CTS, filler removal,
# obstruction deletion, architecture change, or rule relaxation.
set out $::env(PINXY_OUTPUT)
set stages [open $out/isolated_geometry_size_and_legalization.stages.tsv w]
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

set selected [dict create]
dict set selected {_319006_} {NOR2_X2}
dict set selected {_330558_} {NAND2_X2}
dict set selected {_330742_} {NOR2_X2}
dict set selected {_369240_} {NAND2_X4}
dict set selected {_446549_} {AND2_X2}
dict set selected {_446553_} {AND2_X2}
dict set selected {_446555_} {AND2_X2}
dict set selected {_446556_} {AND2_X2}
dict set selected {_446559_} {AND2_X2}
dict set selected {_446562_} {AND2_X2}
dict set selected {_446690_} {MUX2_X2}
dict set selected {_457170_} {MUX2_X2}
dict set selected {_457487_} {AND3_X2}
dict set selected {_457506_} {AND3_X2}
dict set selected {_462288_} {NAND2_X2}
dict set selected {_464497_} {NOR4_X4}
dict set selected {_465996_} {NAND2_X2}
dict set selected {_468775_} {NAND2_X2}
dict set selected {_469008_} {OAI21_X4}
dict set selected {_469030_} {NAND2_X2}
dict set selected {_471163_} {NOR2_X4}
dict set selected {_473139_} {NAND2_X2}
dict set selected {_478291_} {NAND2_X2}
dict set selected {_484454_} {OAI22_X2}
dict set selected {_496609_} {NOR2_X2}
dict set selected {_501946_} {NOR2_X2}
dict set selected {_502176_} {NOR2_X2}
dict set selected {_502230_} {OAI21_X2}
dict set selected {_502239_} {AOI21_X2}
dict set selected {_502268_} {AOI21_X2}
dict set selected {_505004_} {AND2_X2}
dict set selected {c_r\[25\]$_DFFE_PN0P_} {DFFR_X2}
dict set selected {output1284} {BUF_X2}
dict set selected {output1289} {BUF_X2}
dict set selected {output1293} {BUF_X2}
dict set selected {output1396} {BUF_X2}
dict set selected {output1398} {BUF_X2}
dict set selected {output1402} {BUF_X2}
dict set selected {output1406} {BUF_X2}
dict set selected {output1411} {BUF_X2}
dict set selected {output1413} {BUF_X2}
dict set selected {output1414} {BUF_X2}
dict set selected {place112672} {BUF_X2}
dict set selected {place143814} {BUF_X2}
dict set selected {place145328} {BUF_X2}
dict set selected {place145435} {BUF_X2}
dict set selected {place145878} {BUF_X2}
dict set selected {place146166} {BUF_X2}
dict set selected {place146243} {BUF_X2}
dict set selected {place146398} {BUF_X2}
dict set selected {place147655} {BUF_X2}
dict set selected {place147925} {BUF_X2}
dict set selected {place148023} {BUF_X4}
dict set selected {place148481} {BUF_X2}
dict set selected {place149324} {BUF_X2}
dict set selected {place149455} {BUF_X2}
dict set selected {place149783} {BUF_X2}
dict set selected {place151749} {BUF_X2}
dict set selected {place152199} {BUF_X2}
dict set selected {place152232} {BUF_X2}
dict set selected {place153673} {BUF_X2}
dict set selected {wr_data_r\[201\]$_DFFE_PN0P_} {DFFR_X2}
dict set selected {wr_data_r\[202\]$_DFFE_PN0P_} {DFFR_X2}
dict set selected {wr_data_r\[32\]$_DFFE_PN0P_} {DFFR_X2}
dict set selected {wr_data_r\[33\]$_DFFE_PN0P_} {DFFR_X2}
dict set selected {wr_data_r\[34\]$_DFFE_PN0P_} {DFFR_X2}
dict set selected {wr_data_r\[36\]$_DFFE_PN0P_} {DFFR_X2}
dict set selected {wr_data_r\[39\]$_DFFE_PN0P_} {DFFR_X2}
dict set selected {wr_data_r\[42\]$_DFFE_PN0P_} {DFFR_X2}
dict set selected {wr_data_r\[45\]$_DFFE_PN0P_} {DFFR_X2}
dict set selected {wr_data_r\[46\]$_DFFE_PN0P_} {DFFR_X2}
dict set selected {y2_r\[111\]$_DFFE_PN0P_} {DFFR_X2}
dict set selected {y2_r\[226\]$_DFFE_PN0P_} {DFFR_X2}
dict set selected {y2_r\[39\]$_DFFE_PN0P_} {DFFR_X2}
dict set selected {y2_r\[49\]$_DFFE_PN0P_} {DFFR_X2}

read_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/vector_resume/r01/routed.odb}
set b [ord::get_db_block];set statuses [dict create];set filler_masters {}
foreach i [$b getInsts] {set name [$i getName];if {[[$i getMaster] getType] eq "CORE_SPACER"} {lappend filler_masters [[$i getMaster] getName];continue};dict set statuses $name [$i getPlacementStatus]}
set filler_masters [lsort -unique $filler_masters];remove_fillers
foreach i [$b getInsts] {set name [$i getName];if {[dict exists $selected $name]} {set m [[ord::get_db] findMaster [dict get $selected $name]];if {$m eq "NULL" || ![$i swapMaster $m]} {error "Size swap failed"};$i setPlacementStatus PLACED} else {$i setPlacementStatus LOCKED}}
if {![stage isolated_legalization {detailed_placement -use_diamond_legalizer;check_placement -verbose}]} {close $stages;exit 1}
dict for {name status} $statuses {[$b findInst $name] setPlacementStatus $status}
set f [open {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/current_driver_sizing/r04/vector/actual_size_poses.tcl} w];puts $f [list set filler_masters $filler_masters];dict for {name master} $selected {set i [$b findInst $name];lassign [$i getLocation] x y;puts $f [list lappend size_replay [list $name $master $x $y [$i getPlacementStatus]]]};close $f
fingerprint {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/current_driver_sizing/r04/vector/placed}
write_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/current_driver_sizing/r04/vector/placed_NOT_ROUTED.odb}
close $stages

