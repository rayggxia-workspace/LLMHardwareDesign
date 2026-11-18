set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
set src $root/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-m10/reroute-v2/patched.odb
read_sdc $src/6_final.sdc
set_propagated_clock [all_clocks]
source $platform/setRC.tcl
source $root/geometry.tcl
geometry_snapshot geometry-before.tsv
source $root/c-freeze-outputs-v1.tcl
freeze_selected_c_outputs
remove_fillers
set b [ord::get_db_block]
set f [open $root/c-v27-electrical-plan.tsv];gets $f header
set count 0
while {[gets $f line]>=0} {
 lassign [split $line "\t"] name old term net strategy xy
 set i [$b findInst $name]
 if {$i eq "NULL" || [[$i getMaster] getName] ne $old} {error "Actual driver master mismatch $name"}
 set it [$i findITerm $term]
 if {$it eq "NULL" || [[$it getNet] getName] ne $net} {error "Actual driver topology mismatch $name/$term"}
 if {$strategy eq "resize"} {
  if {$term ne "Z" || $old ni {BUF_X1 BUF_X2 BUF_X4 CLKBUF_X1 CLKBUF_X3}} {error "Non-buffer replacement refused"}
  replace_cell $name BUF_X$::env(C_STRENGTH)
  incr count
 }
}
close $f
if {$count!=276} {error "Driver resize scope changed"}
set bad [$b findInst _287569_]
if {$bad eq "NULL" || [[$bad getMaster] getName] ne "OAI221_X4"} {error "Physical defect source mismatch"}
replace_cell _287569_ OAI221_X2
freeze_selected_c_outputs
geometry_snapshot geometry-after.tsv
exec cmp geometry-before.tsv geometry-after.tsv
set fp [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-static-greedy-v3/cumulative-plan-from-X8.tsv];gets $fp header
set nplan 0
while {[gets $fp line]>=0} {
 lassign [split $line "\t"] name old new
 set i [$b findInst $name]
 if {$i eq "NULL" || [[$i getMaster] getName] ne $old || $new eq "OAI221_X4"} {error "Frozen greedy plan does not match $name"}
 replace_cell $name $new
 incr nplan
}
close $fp
if {$nplan!=91} {error "Cumulative plan count mismatch"}
freeze_selected_c_outputs
read_spef /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-rcx-normalization-v2/reextract-encoder/isolated.spef
sta::find_timing
set f [open static-counts.tsv w]
foreach mode {max min} {puts $f "$mode\t[sta::endpoint_violation_count $mode]"}
foreach kind {capacitance slew fanout} {puts $f "$kind\t[sta::max_${kind}_violation_count]"}
close $f
report_check_types -max_capacitance -max_slew -violators -digits 9 > static-electrical.rpt
report_worst_slack -max -digits 9 > static-setup.rpt
report_worst_slack -min -digits 9 > static-hold.rpt
report_checks -path_delay min_max -group_path_count 20 -digits 9 > static-paths.rpt
write_db resized.odb
write_verilog resized.v
puts STATIC_WIRE_MODEL_CHARACTERIZATION_ONLY_PENDING_ISOLATION_LEGALIZE_ROUTE_EXTRACT
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
puts STATIC_WIRE_PLANNING_ONLY_NO_POSTLAYOUT_CLAIM
