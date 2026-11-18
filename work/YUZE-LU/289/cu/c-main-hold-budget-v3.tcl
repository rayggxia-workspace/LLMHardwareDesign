set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
set src $root/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base
read_db $src/6_final.odb
read_sdc $src/6_final.sdc
read_spef $root/diagnostics/C-main-v1-rcx/results/6_final.spef
set_propagated_clock [all_clocks]
sta::find_timing
set b [ord::get_db_block]
proc net_signature {net} {
 set a {}
 foreach it [$net getITerms] {set i [$it getInst];lappend a [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [[$it getMTerm] getName]]}
 foreach bt [$net getBTerms] {lappend a [list BTERM [$bt getName]]}
 return [lsort $a]
}
set signatures {}
foreach n [$b getNets] {if {[$n getSigType] ni {POWER GROUND}} {dict set signatures [$n getName] [net_signature $n]}}
set f [open original-signatures.tcllist w];puts $f [list $signatures];close $f
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
puts APPROXIMATE_PLANNING_ONLY_TWO_RCX_CORNER_DIFFERENCES_PENDING_CANONICAL_FIX
