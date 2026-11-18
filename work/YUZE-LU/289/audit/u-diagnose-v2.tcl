set_thread_count 2
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(U_LIBS) {read_liberty $lib}
set res $::env(U_RESULTS)
read_db $res/6_final.odb
read_sdc $res/6_final.sdc
read_spef $res/6_final.spef
set_propagated_clock [all_clocks]
report_checks -path_delay min -format full_clock_expanded -group_path_count 20 -digits 9 > hold-paths.rpt
report_checks -path_delay max -format full_clock_expanded -group_path_count 10 -digits 9 > setup-paths.rpt
set block [ord::get_db_block]
set f [open electrical-net-drivers.tsv w]
set e [open $::env(U_RUN)/electrical.rpt];set pins {};foreach line [split [read $e] "\n"] {if {[regexp {^(\S+)\s+[0-9.]+.*\(VIOLATED\)} $line -> pin]} {lappend pins $pin}};close $e
foreach name [lsort -unique $pins] {
 set it [$block findITerm $name]
 if {$it eq "NULL"} {
  set bt [$block findBTerm $name];if {$bt eq "NULL"} {error "Missing pin $name"}
  set n [$bt getNet];puts $f "EXTERNAL_PORT\t$name\t[$bt getIoType]"
 } else {set n [$it getNet]}
 puts $f "PIN\t$name\tNET\t[$n getName]"
 foreach t [$n getITerms] {
  set inst [$t getInst]
  puts $f "TERM\t[$inst getName]\t[[$inst getMaster] getName]\t[[$t getMTerm] getName]\t[[$t getMTerm] getIoType]"
 }
}
close $f
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 9 > fresh-electrical.rpt
report_check_types -recovery -removal -violators -verbose -digits 9 > fresh-async.rpt
report_worst_slack -min -digits 9 > fresh-hold.rpt
report_worst_slack -max -digits 9 > fresh-setup.rpt
