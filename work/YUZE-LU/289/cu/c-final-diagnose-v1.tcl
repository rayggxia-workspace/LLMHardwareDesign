set_thread_count 8
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
 if {$it eq "NULL" && [string last / $name]>=0} {
  set sep [string last / $name];set instname [string range $name 0 [expr {$sep-1}]];set pinname [string range $name [expr {$sep+1}] end];set matches {}
  foreach instance [$block getInsts] {if {[string map [list "\\" ""] [$instance getName]] eq $instname} {lappend matches $instance}}
  if {[llength $matches]==1} {set it [[lindex $matches 0] findITerm $pinname]}
 }
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

sta::find_timing
set b [ord::get_db_block]
set instances {}
foreach i [$b getInsts] {dict set instances [string map [list "\\" ""] [$i getName]] $i}
set f [open hold-setup-budget.tsv w]
puts $f "endpoint\tinstance\tterminal\tmin_slack_ns\tmax_slack_ns\tstatus"
set seen {};set ndata 0
# Capture endpoint pins/slacks before nested max queries invalidate path handles.
set records {}
foreach path [find_timing_paths -path_delay min -slack_max 0 -group_path_count 10000 -endpoint_path_count 1] {
 lappend records [list [get_property $path endpoint] [get_property $path slack]]
}
foreach record $records {
 lassign $record pin hs
 set name [string map [list "\\" ""] [get_full_name $pin]]
 if {[dict exists $seen $name]} {continue}
 dict set seen $name 1
 set slash [string last / $name]
 set iname [string range $name 0 [expr {$slash-1}]]
 set term [string range $name [expr {$slash+1}] end]
 if {$slash<0 || ![dict exists $instances $iname]} {
  puts $f "$name\t$iname\t$term\t$hs\tNA\tseparate_review"
  continue
 }
 set inst [dict get $instances $iname]
 set eligible [expr {$term eq "D" && [string match DFF* [[$inst getMaster] getName]]}]
 if {!$eligible && [[$inst getMaster] isBlock] && $iname eq {services.engine[0].element.arithmetic.leaf} && [regexp {^in_data\[[0-9]+\]$} $term]} {set eligible 1}
 if {!$eligible} {
  puts $f "$name\t$iname\t$term\t$hs\tNA\tseparate_review"
  continue
 }
 set mx [find_timing_paths -to $pin -path_delay max -group_path_count 1]
 if {[llength $mx]!=1} {error "No exact setup budget $name"}
 set ss [get_property [lindex $mx 0] slack]
 puts $f "$name\t[$inst getName]\t$term\t$hs\t$ss\tdata"
 incr ndata
}
close $f
puts "ACTUAL_SOURCE_HOLD_PLAN unique=[dict size $seen] D_sinks=$ndata"
puts PLANNING_ONLY_PENDING_INDEPENDENT_RCX_GEOMETRY_GATE

foreach ep {{memory_service.actor2.loader.cached_addr[1][60]$_SDFFCE_PN0P_/D} {memory_service.actor2.loader.pd[0][94]$_DFFE_PP_/D} {memory_service.memory.indexed.read_address[63]$_SDFFE_PN0P_/D}} tag {cache60 pd94 indexed63} {
 report_checks -to [get_pins $ep] -path_delay max -group_path_count 1 -fields {input_pin slew cap fanout net} -digits 9 > $tag.rpt
}
report_checks -path_delay max -group_path_count 150 -fields {input_pin slew cap fanout net} -digits 9 > all-setup-paths.rpt
