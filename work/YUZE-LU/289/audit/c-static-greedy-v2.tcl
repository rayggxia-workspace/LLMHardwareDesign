set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
set cu $root/cu
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db input.odb
set src $cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base
read_sdc $src/6_final.sdc
set_propagated_clock [all_clocks]
source $platform/setRC.tcl
source $cu/c-freeze-outputs-v1.tcl
freeze_selected_c_outputs
source choices.tcl
set b [ord::get_db_block]
set original {};set inst_by_name {};set protected {};set queue {};set visited {}
foreach i [$b getInsts] {
 set n [$i getName];dict set original $n [[$i getMaster] getName]
 set normalized [string map [list "\\" ""] $n]
 if {[dict exists $inst_by_name $normalized]} {error "Ambiguous normalized instance $n"}
 dict set inst_by_name $normalized $i
 if {[[$i getMaster] isBlock] || [$i isDoNotTouch]} {dict set protected $n 1}
 foreach it [$i getITerms] {
  if {[[$it getMTerm] getName] in {CK CLK clk clk_i clock}} {set net [$it getNet];if {$net ne "NULL"} {lappend queue $net}}
 }
}
foreach bt [$b getBTerms] {
 if {[$bt getIoType] ni {OUTPUT INOUT}} {continue}
 set net [$bt getNet];if {$net eq "NULL"} {continue}
 foreach it [$net getITerms] {if {[[$it getMTerm] getIoType] eq "OUTPUT"} {dict set protected [[$it getInst] getName] 1}}
}
while {[llength $queue]} {
 set net [lindex $queue end];set queue [lrange $queue 0 end-1]
 set n [$net getName];if {[dict exists $visited $n]} {continue};dict set visited $n 1
 foreach it [$net getITerms] {
  if {[[$it getMTerm] getIoType] ne "OUTPUT"} {continue}
  set i [$it getInst];dict set protected [$i getName] 1
  if {[[$i getMaster] isBlock] || [regexp {^(DFF|SDFF|DFFR|DFFS|DLH|DLL)} [[$i getMaster] getName]]} {continue}
  foreach ip [$i getITerms] {if {[[$ip getMTerm] getIoType] eq "INPUT"} {set nn [$ip getNet];if {$nn ne "NULL"} {lappend queue $nn}}}
 }
}
set f [open protected-instances.txt w];foreach n [lsort [dict keys $protected]] {puts $f $n};close $f
proc topology {file} {
 set f [open $file w]
 foreach i [[ord::get_db_block] getInsts] {
  set pins {}
  foreach it [$i getITerms] {set net [$it getNet];set nn NULL;if {$net ne "NULL"} {set nn [$net getName]};lappend pins "[[$it getMTerm] getName]=$nn"}
  lassign [$i getLocation] x y
  puts $f [join [list [$i getName] [[$i getMaster] getName] $x $y [$i getOrient] [join [lsort $pins] |]] "\t"]
 }
 close $f
}
topology topology-before.tsv
source $cu/geometry.tcl
geometry_snapshot geometry-before.tsv
read_spef $src/6_final.spef
proc last_number {file} {
 set f [open $file];set s [string trim [read $f]];close $f
 if {![regexp {([-+]?[0-9]+\.[0-9]+(?:[eE][-+]?[0-9]+)?)\s*$} $s -> n]} {error "Unparsed timing metric $file: $s"}
 return $n
}
proc metrics {} {
 sta::find_timing
 report_worst_slack -max -digits 9 > metric-wns.rpt
 report_tns -digits 9 > metric-tns.rpt
 return [list [last_number metric-wns.rpt] [last_number metric-tns.rpt] [sta::max_capacitance_violation_count] [sta::max_slew_violation_count] [sta::endpoint_violation_count max]]
}
set baseline [metrics];set best $baseline;set trial 0;set accepted 0;set start [clock seconds]
report_checks -path_delay max -slack_max 0 -group_path_count 3 -fields {slew cap fanout input_pin net} -digits 9 > baseline-detail.rpt
report_worst_slack -min -digits 9 > baseline-hold.rpt
set log [open trials.tsv w];puts $log "trial\tround\tinstance\told\tnew\twns_ns\ttns_ns\tcap\tslew\tsetup_count\taccepted";flush $log
set f [open baseline-metrics.tsv w];puts $f $baseline;close $f
for {set round 0} {$round<10 && $trial<240 && [clock seconds]-$start<720} {incr round} {
 set todo {};set seen {}
 foreach path [find_timing_paths -path_delay max -slack_max 0 -group_path_count 40 -endpoint_path_count 1] {
  foreach pt [get_property $path points] {
   set pin [get_property $pt pin];set fullname [string map [list "\\" ""] [get_full_name $pin]];set slash [string last / $fullname]
   if {$slash<0} {continue};set name [string range $fullname 0 [expr {$slash-1}]]
   if {![dict exists $inst_by_name $name]} {continue};set i [dict get $inst_by_name $name];set n [$i getName];set old [[$i getMaster] getName]
   if {[dict exists $seen $n] || [dict exists $protected $n] || ![dict exists $equivalents $old]} {continue}
   dict set seen $n 1;lappend todo $n
  }
 }
 if {![llength $todo]} {break}
 set preferred _280589_
 set idx [lsearch -exact $todo $preferred]
 if {$idx>=0} {set todo [linsert [lreplace $todo $idx $idx] 0 $preferred]}
 set round_start_trial $trial
 set improved 0
 foreach n $todo {
  set i [$b findInst $n];set original_step [[$i getMaster] getName]
  if {![dict exists $equivalents $original_step]} {continue}
  foreach new [dict get $equivalents $original_step] {
   if {$trial>=240 || [clock seconds]-$start>=720} {break}
   set old [[$i getMaster] getName]
   replace_cell $n $new
   set now [metrics];lassign $best bw bt bc bs bn;lassign $now nw nt nc ns nn
   set keep [expr {$nw >= $bw-0.000001 && $nt >= $bt-0.000001 && $nc <= $bc && $ns <= $bs && ($nw>$bw+0.000010 || $nt>$bt+0.000010)}]
   incr trial
   puts $log [join [concat [list $trial $round $n $old $new] $now [list $keep]] "\t"];flush $log
   if {$keep} {set best $now;incr accepted;incr improved;puts "ACCEPT $n $old $new $now";flush stdout} else {replace_cell $n $old}
  }
  if {$trial>=240 || [clock seconds]-$start>=720 || $trial-$round_start_trial>=48} {break}
 }
 if {!$improved} {break}
}
close $log
set final [metrics]
set f [open final-metrics.tsv w];puts $f $final;close $f
set f [open plan.tsv w];puts $f "instance\told\tnew"
foreach i [$b getInsts] {
 set n [$i getName];set old [dict get $original $n];set new [[$i getMaster] getName]
 if {$old ne $new} {
  if {[dict exists $protected $n] || ![dict exists $equivalents $old] || $new ni [dict get $equivalents $old]} {error "Out-of-scope replacement $n $old $new"}
  puts $f "$n\t$old\t$new"
 }
}
close $f
freeze_selected_c_outputs
geometry_snapshot geometry-after.tsv
exec cmp geometry-before.tsv geometry-after.tsv
topology topology-after.tsv
write_db best.odb
write_verilog best.v
report_checks -path_delay min_max -group_path_count 20 -digits 9 > final-paths.rpt
report_checks -path_delay max -slack_max 0 -group_path_count 3 -fields {slew cap fanout input_pin net} -digits 9 > final-detail.rpt
report_check_types -max_capacitance -max_slew -violators -digits 9 > final-electrical.rpt
report_worst_slack -min -digits 9 > final-hold.rpt
puts "GREEDY_COMPLETE trials=$trial accepted=$accepted baseline=$baseline final=$final"
puts STATIC_ONLY_PENDING_LEGALIZE_ROUTE_FRESH_EXTRACTION_AND_FINAL_PROOF
