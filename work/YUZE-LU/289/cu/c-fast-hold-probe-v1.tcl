set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
set cu $root/cu
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $root/audit/C-static-greedy-v2/best.odb
set src $cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base
read_sdc $src/6_final.sdc
read_spef $src/6_final.spef
set_propagated_clock [all_clocks]
sta::find_timing
set b [ord::get_db_block]
set lookup {};foreach i [$b getInsts] {dict set lookup [string map [list "\\" ""] [$i getName]] $i}
set protected {};set f [open $root/audit/C-static-greedy-v2/protected-instances.txt]
while {[gets $f line]>=0} {dict set protected $line 1};close $f
set targets {};set f [open $cu/diagnostics/C-actual-edit-pilot-X8-h50-d50/actual-hold-plan.tsv];gets $f header
while {[gets $f line]>=0} {
 lassign [split $line "\t"] inst term hs ss requested chosen strong
 if {$chosen<$requested} {dict set targets [string map [list "\\" ""] $inst]/$term 1}
};close $f
set endpoints {}
foreach path [find_timing_paths -path_delay min -slack_max 0 -group_path_count 10000 -endpoint_path_count 1] {
 set ep [get_property $path endpoint];set name [string map [list "\\" ""] [get_full_name $ep]]
 if {[dict exists $targets $name]} {dict set endpoints $name [list $ep [get_property $path slack]]}
}
set f [open branch-candidates.tsv w]
puts $f "endpoint\tworst_min_ns\tsampled_paths\tpin\tmaster\tdistance\tthrough_max_budget_ns"
set out [open branch-plan.tsv w]
puts $out "endpoint\tmin_slack_ns\tbranch_instance\tbranch_terminal\tthrough_max_budget_ns\tsampled_paths\tstatus"
set idx 0;set selected 0
foreach {name info} $endpoints {
 lassign $info ep hs
 set paths [find_timing_paths -to $ep -path_delay min -slack_max 0 -group_path_count 40 -endpoint_path_count 40]
 set np [llength $paths];set counts {};set distances {};set pins {};set its {}
 foreach path $paths {
  set pts [get_property $path points];set pos 0;set seen {}
  foreach pt $pts {
   incr pos
   set pin [get_property $pt pin];set full [string map [list "\\" ""] [get_full_name $pin]]
   set slash [string last / $full];if {$slash<0} {continue}
   set iname [string range $full 0 [expr {$slash-1}]];set term [string range $full [expr {$slash+1}] end]
   if {![dict exists $lookup $iname]} {continue}
   set inst [dict get $lookup $iname];set master [$inst getMaster]
   if {[$master isBlock] || [dict exists $protected [$inst getName]] || [regexp {^(DFF|SDFF|DFFR|DFFS|DLH|DLL|CLKGATE)} [$master getName]]} {continue}
   set it [$inst findITerm $term]
   if {$it eq "NULL" || [[$it getMTerm] getIoType] ne "INPUT" || [$it getNet] eq "NULL" || [[$it getNet] getSigType] ne "SIGNAL"} {continue}
   if {[dict exists $seen $full]} {continue};dict set seen $full 1
   dict incr counts $full
   dict set distances $full [expr {[llength $pts]-$pos}]
   dict set pins $full $pin;dict set its $full $it
  }
 }
 set todo {}
 foreach {full n} $counts {if {$n==$np} {lappend todo [list [dict get $distances $full] $full]}}
 set todo [lsort -integer -index 0 $todo]
 set chosen {};set trials 0
 foreach item $todo {
  incr trials;if {$trials>30} {break}
  lassign $item dist full;set pin [dict get $pins $full];set it [dict get $its $full]
  set mx [find_timing_paths -through $pin -path_delay max -group_path_count 1 -endpoint_path_count 1]
  if {![llength $mx]} {continue}
  set slack 1e9
  foreach path $mx {set v [get_property $path slack];if {$v<$slack} {set slack $v}}
  puts $f "$name\t$hs\t$np\t$full\t[[[$it getInst] getMaster] getName]\t$dist\t$slack"
  set required [expr {.100+.040*ceil((-$hs+.150)/.020)}]
  if {$slack>=$required && ![llength $chosen]} {set chosen [list [[$it getInst] getName] [[$it getMTerm] getName] $slack]}
 }
 if {[llength $chosen]} {
  lassign $chosen ci ct cs
  puts $out "$name\t$hs\t$ci\t$ct\t$cs\t$np\tsampled_common_with_budget"
  incr selected
 } else {puts $out "$name\t$hs\tNA\tNA\tNA\t$np\tno_safe_common_sampled_branch"}
 report_checks -to $ep -path_delay min -slack_max 0 -group_path_count 3 -endpoint_path_count 3 -fields {slew cap fanout input_pin net} -digits 9 > endpoint-${idx}-min.rpt
 report_checks -to $ep -path_delay max -group_path_count 1 -fields {slew cap fanout input_pin net} -digits 9 > endpoint-${idx}-max.rpt
 incr idx
}
close $f;close $out
puts "FAST_BRANCH_PLANNING targets=[dict size $targets] negative=[dict size $endpoints] sampled_common_with_budget=$selected"
puts NO_EDITS_NO_EXHAUSTIVE_PATH_COVERAGE_OR_SIGNOFF_CLAIM_FINAL_FULL_STA_REQUIRED
