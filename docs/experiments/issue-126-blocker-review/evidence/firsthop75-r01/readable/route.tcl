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
read_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_pin_retention/r01/routed.odb}
set_routing_layers -signal metal2-metal8 -clock metal4-metal8
fingerprint {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_first_hop_reroute/r01/before}
set b [ord::get_db_block];set original_obs [lsort [$b getObstructions]];set selected_names {}
if {![stage actual75_pin_edits {
set bt [$b findBTerm {bit_1052}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1052}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1052} -layer metal5 -location {280.375 849.59} -pin_size {.14 .14}
lappend selected_names {bit_1052}
set bt [$b findBTerm {bit_1100}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1100}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1100} -layer metal5 -location {342.255 665.91} -pin_size {.14 .14}
lappend selected_names {bit_1100}
set bt [$b findBTerm {bit_1103}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1103}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1103} -layer metal5 -location {348.415 665.91} -pin_size {.14 .14}
lappend selected_names {bit_1103}
set bt [$b findBTerm {bit_1172}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1172}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1172} -layer metal5 -location {334.695 883.19} -pin_size {.14 .14}
lappend selected_names {bit_1172}
set bt [$b findBTerm {bit_1312092}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1312092}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1312092} -layer metal6 -location {199.455 1427.27} -pin_size {.14 .14}
lappend selected_names {bit_1312092}
set bt [$b findBTerm {bit_1312322}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1312322}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1312322} -layer metal5 -location {181.535 1396.15} -pin_size {.14 .14}
lappend selected_names {bit_1312322}
set bt [$b findBTerm {bit_1313134}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1313134}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1313134} -layer metal5 -location {408.895 1877.75} -pin_size {.14 .14}
lappend selected_names {bit_1313134}
set bt [$b findBTerm {bit_1313281}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1313281}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1313281} -layer metal6 -location {851.295 2023.27} -pin_size {.14 .14}
lappend selected_names {bit_1313281}
set bt [$b findBTerm {bit_1313368}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1313368}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1313368} -layer metal6 -location {283.455 1371.27} -pin_size {.14 .14}
lappend selected_names {bit_1313368}
set bt [$b findBTerm {bit_1352369}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1352369}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1352369} -layer metal5 -location {711.855 948.15} -pin_size {.14 .14}
lappend selected_names {bit_1352369}
set bt [$b findBTerm {bit_1352802}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1352802}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1352802} -layer metal6 -location {491.495 945.67} -pin_size {.14 .14}
lappend selected_names {bit_1352802}
set bt [$b findBTerm {bit_1352844}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1352844}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1352844} -layer metal6 -location {459.295 1225.67} -pin_size {.14 .14}
lappend selected_names {bit_1352844}
set bt [$b findBTerm {bit_1352850}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1352850}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1352850} -layer metal6 -location {455.935 1228.07} -pin_size {.14 .14}
lappend selected_names {bit_1352850}
set bt [$b findBTerm {bit_1353041}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1353041}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1353041} -layer metal5 -location {399.095 867.51} -pin_size {.14 .14}
lappend selected_names {bit_1353041}
set bt [$b findBTerm {bit_1381973}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1381973}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1381973} -layer metal5 -location {1564.735 851.83} -pin_size {.14 .14}
lappend selected_names {bit_1381973}
set bt [$b findBTerm {bit_1382130}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1382130}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1382130} -layer metal5 -location {1853.975 636.79} -pin_size {.14 .14}
lappend selected_names {bit_1382130}
set bt [$b findBTerm {bit_1382933}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1382933}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1382933} -layer metal5 -location {1403.735 717.43} -pin_size {.14 .14}
lappend selected_names {bit_1382933}
set bt [$b findBTerm {bit_1382959}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1382959}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1382959} -layer metal5 -location {1451.895 287.35} -pin_size {.14 .14}
lappend selected_names {bit_1382959}
set bt [$b findBTerm {bit_1383461}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1383461}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1383461} -layer metal5 -location {1420.815 157.15} -pin_size {.14 .14}
lappend selected_names {bit_1383461}
set bt [$b findBTerm {bit_1385294}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1385294}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1385294} -layer metal5 -location {1628.015 226.87} -pin_size {.14 .14}
lappend selected_names {bit_1385294}
set bt [$b findBTerm {bit_1385431}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1385431}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1385431} -layer metal5 -location {1614.855 220.15} -pin_size {.14 .14}
lappend selected_names {bit_1385431}
set bt [$b findBTerm {bit_1385650}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1385650}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1385650} -layer metal6 -location {1423.335 676.87} -pin_size {.14 .14}
lappend selected_names {bit_1385650}
set bt [$b findBTerm {bit_1385685}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1385685}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1385685} -layer metal6 -location {1510.695 228.87} -pin_size {.14 .14}
lappend selected_names {bit_1385685}
set bt [$b findBTerm {bit_1389324}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1389324}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1389324} -layer metal5 -location {1745.055 827.19} -pin_size {.14 .14}
lappend selected_names {bit_1389324}
set bt [$b findBTerm {bit_1389434}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1389434}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1389434} -layer metal5 -location {1480.735 231.63} -pin_size {.14 .14}
lappend selected_names {bit_1389434}
set bt [$b findBTerm {bit_1389474}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1389474}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1389474} -layer metal5 -location {1615.975 860.79} -pin_size {.14 .14}
lappend selected_names {bit_1389474}
set bt [$b findBTerm {bit_1389521}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1389521}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1389521} -layer metal5 -location {1417.455 658.91} -pin_size {.14 .14}
lappend selected_names {bit_1389521}
set bt [$b findBTerm {bit_1391439}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1391439}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1391439} -layer metal6 -location {1775.295 824.87} -pin_size {.14 .14}
lappend selected_names {bit_1391439}
set bt [$b findBTerm {bit_1391725}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1391725}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1391725} -layer metal5 -location {1894.855 570.99} -pin_size {.14 .14}
lappend selected_names {bit_1391725}
set bt [$b findBTerm {bit_2691}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_2691}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_2691} -layer metal5 -location {556.735 63.35} -pin_size {.14 .14}
lappend selected_names {bit_2691}
set bt [$b findBTerm {bit_2695}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_2695}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_2695} -layer metal5 -location {565.415 63.35} -pin_size {.14 .14}
lappend selected_names {bit_2695}
set bt [$b findBTerm {bit_2697}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_2697}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_2697} -layer metal5 -location {570.175 63.35} -pin_size {.14 .14}
lappend selected_names {bit_2697}
set bt [$b findBTerm {bit_2819}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_2819}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_2819} -layer metal5 -location {2053.055 538.23} -pin_size {.14 .14}
lappend selected_names {bit_2819}
set bt [$b findBTerm {bit_3144}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_3144}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_3144} -layer metal6 -location {428.775 474.47} -pin_size {.14 .14}
lappend selected_names {bit_3144}
set bt [$b findBTerm {bit_3183}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_3183}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_3183} -layer metal6 -location {518.655 931.27} -pin_size {.14 .14}
lappend selected_names {bit_3183}
set bt [$b findBTerm {bit_329}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_329}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_329} -layer metal6 -location {490.375 612.07} -pin_size {.14 .14}
lappend selected_names {bit_329}
set bt [$b findBTerm {bit_3552}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_3552}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_3552} -layer metal5 -location {478.055 1173.27} -pin_size {.14 .14}
lappend selected_names {bit_3552}
set bt [$b findBTerm {bit_3596}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_3596}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_3596} -layer metal5 -location {420.375 559.51} -pin_size {.14 .14}
lappend selected_names {bit_3596}
set bt [$b findBTerm {bit_3696}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_3696}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_3696} -layer metal5 -location {396.855 787.99} -pin_size {.14 .14}
lappend selected_names {bit_3696}
set bt [$b findBTerm {bit_3735}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_3735}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_3735} -layer metal5 -location {447.815 812.63} -pin_size {.14 .14}
lappend selected_names {bit_3735}
set bt [$b findBTerm {bit_3876}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_3876}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_3876} -layer metal6 -location {563.175 962.47} -pin_size {.14 .14}
lappend selected_names {bit_3876}
set bt [$b findBTerm {bit_410}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_410}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_410} -layer metal6 -location {1111.135 284.87} -pin_size {.14 .14}
lappend selected_names {bit_410}
set bt [$b findBTerm {bit_4182}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_4182}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_4182} -layer metal5 -location {517.535 1251.67} -pin_size {.14 .14}
lappend selected_names {bit_4182}
set bt [$b findBTerm {bit_4449}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_4449}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_4449} -layer metal5 -location {579.135 1235.99} -pin_size {.14 .14}
lappend selected_names {bit_4449}
set bt [$b findBTerm {bit_4581}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_4581}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_4581} -layer metal6 -location {479.455 1018.47} -pin_size {.14 .14}
lappend selected_names {bit_4581}
set bt [$b findBTerm {bit_4587}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_4587}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_4587} -layer metal6 -location {417.575 460.87} -pin_size {.14 .14}
lappend selected_names {bit_4587}
set bt [$b findBTerm {bit_5222}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_5222}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_5222} -layer metal6 -location {508.575 1188.87} -pin_size {.14 .14}
lappend selected_names {bit_5222}
set bt [$b findBTerm {bit_5233}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_5233}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_5233} -layer metal6 -location {408.895 796.87} -pin_size {.14 .14}
lappend selected_names {bit_5233}
set bt [$b findBTerm {bit_5342}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_5342}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_5342} -layer metal6 -location {956.575 1278.47} -pin_size {.14 .14}
lappend selected_names {bit_5342}
set bt [$b findBTerm {bit_5382}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_5382}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_5382} -layer metal6 -location {589.215 964.87} -pin_size {.14 .14}
lappend selected_names {bit_5382}
set bt [$b findBTerm {bit_5416}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_5416}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_5416} -layer metal6 -location {513.895 931.27} -pin_size {.14 .14}
lappend selected_names {bit_5416}
set bt [$b findBTerm {bit_5423}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_5423}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_5423} -layer metal6 -location {474.695 794.47} -pin_size {.14 .14}
lappend selected_names {bit_5423}
set bt [$b findBTerm {bit_5660}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_5660}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_5660} -layer metal5 -location {1543.455 208.95} -pin_size {.14 .14}
lappend selected_names {bit_5660}
set bt [$b findBTerm {bit_5661}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_5661}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_5661} -layer metal5 -location {1545.695 208.95} -pin_size {.14 .14}
lappend selected_names {bit_5661}
set bt [$b findBTerm {bit_5686}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_5686}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_5686} -layer metal5 -location {1549.895 215.67} -pin_size {.14 .14}
lappend selected_names {bit_5686}
set bt [$b findBTerm {bit_5777}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_5777}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_5777} -layer metal5 -location {1518.535 670.39} -pin_size {.14 .14}
lappend selected_names {bit_5777}
set bt [$b findBTerm {bit_6492}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_6492}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_6492} -layer metal5 -location {1589.095 585.27} -pin_size {.14 .14}
lappend selected_names {bit_6492}
set bt [$b findBTerm {bit_6539}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_6539}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_6539} -layer metal5 -location {1505.095 706.23} -pin_size {.14 .14}
lappend selected_names {bit_6539}
set bt [$b findBTerm {bit_6705}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_6705}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_6705} -layer metal6 -location {1554.655 231.27} -pin_size {.14 .14}
lappend selected_names {bit_6705}
set bt [$b findBTerm {bit_6777}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_6777}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_6777} -layer metal6 -location {1627.455 600.87} -pin_size {.14 .14}
lappend selected_names {bit_6777}
set bt [$b findBTerm {bit_7032}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_7032}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_7032} -layer metal5 -location {1616.535 538.23} -pin_size {.14 .14}
lappend selected_names {bit_7032}
set bt [$b findBTerm {bit_7153}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_7153}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_7153} -layer metal5 -location {1643.695 589.75} -pin_size {.14 .14}
lappend selected_names {bit_7153}
set bt [$b findBTerm {bit_7193}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_7193}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_7193} -layer metal5 -location {1537.855 681.59} -pin_size {.14 .14}
lappend selected_names {bit_7193}
set bt [$b findBTerm {bit_7211}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_7211}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_7211} -layer metal5 -location {1541.495 249.27} -pin_size {.14 .14}
lappend selected_names {bit_7211}
set bt [$b findBTerm {bit_7215}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_7215}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_7215} -layer metal5 -location {1550.175 249.27} -pin_size {.14 .14}
lappend selected_names {bit_7215}
set bt [$b findBTerm {bit_724}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_724}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_724} -layer metal5 -location {361.575 883.19} -pin_size {.14 .14}
lappend selected_names {bit_724}
set bt [$b findBTerm {bit_7382}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_7382}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_7382} -layer metal6 -location {1755.135 824.87} -pin_size {.14 .14}
lappend selected_names {bit_7382}
set bt [$b findBTerm {bit_785}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_785}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_785} -layer metal6 -location {344.775 1015.27} -pin_size {.14 .14}
lappend selected_names {bit_785}
set bt [$b findBTerm {bit_830}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_830}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_830} -layer metal6 -location {329.095 768.87} -pin_size {.14 .14}
lappend selected_names {bit_830}
set bt [$b findBTerm {bit_954}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_954}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_954} -layer metal5 -location {230.815 464.31} -pin_size {.14 .14}
lappend selected_names {bit_954}
set bt [$b findBTerm {bit_955}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_955}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_955} -layer metal5 -location {233.055 464.31} -pin_size {.14 .14}
lappend selected_names {bit_955}
set bt [$b findBTerm {bit_959}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_959}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_959} -layer metal5 -location {242.015 464.31} -pin_size {.14 .14}
lappend selected_names {bit_959}
set bt [$b findBTerm {bit_975}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_975}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_975} -layer metal5 -location {322.375 710.71} -pin_size {.14 .14}
lappend selected_names {bit_975}
set bt [$b findBTerm {bit_994}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_994}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_994} -layer metal5 -location {312.575 717.71} -pin_size {.14 .14}
lappend selected_names {bit_994}
set bt [$b findBTerm {bit_1011}];if {$bt eq "NULL" || [[$bt getNet] getName] ne {bit_1011}} {error "Actual pin peer net changed"}
place_pin -pin_name {bit_1011} -layer metal5 -location {339.735 1062.39} -pin_size {.14 .14}
lappend selected_names {bit_1011}
}]} {close $stages;exit 1}
fingerprint {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_first_hop_reroute/r01/moved}
read_guides {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_first_hop_reroute/r01/route.guide}
set_nets_to_route $selected_names
if {![stage selected75_actual_detailed_route {detailed_route -output_drc {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_first_hop_reroute/r01/route.drc} -verbose 1}]} {catch {write_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_first_hop_reroute/r01/failed_route.odb}};close $stages;exit 1}
if {[lsort [$b getObstructions]] ne $original_obs} {error "Original OBS changed"}
fingerprint {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_first_hop_reroute/r01/after}
write_db {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_first_hop_reroute/r01/routed.odb}
write_def {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_first_hop_reroute/r01/routed.def}
stage VDD {check_power_grid -net VDD -error_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_first_hop_reroute/r01/VDD.rpt}}
stage VSS {check_power_grid -net VSS -error_file {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_first_hop_reroute/r01/VSS.rpt}}
source {/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/drivers/deadline-firsthop75-r01/export_access.tcl}
close $stages
