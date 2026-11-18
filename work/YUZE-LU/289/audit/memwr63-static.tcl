set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $root/audit/C-v28-nine-net-normalization-v1/reextract-encoder/before.odb
read_sdc $root/cu/runs/C-v28-actual-i8-h50/flow/results/nangate45/c-overlay-current/base/6_final.sdc
read_spef $root/audit/C-v28-nine-net-normalization-v1/reextract-encoder/isolated.spef
set_propagated_clock [all_clocks]
source $root/audit/C-final-v1/geometry-all.tcl
source $root/cu/c-freeze-outputs-v1.tcl
freeze_selected_c_outputs
source choices.tcl
set target {}
foreach port [get_ports *] {if {[get_full_name $port] eq {mem_wr_address[63]}} {lappend target $port}}
if {[llength $target]!=1} {error "Missing unique mem_wr_address63 port"}
set target [lindex $target 0]
set b [ord::get_db_block];set instances {};set protected {};set queue {};set visited {}
foreach i [$b getInsts] {
 set n [$i getName];set normalized [string map [list "\\" ""] $n]
 if {[dict exists $instances $normalized]} {error "Ambiguous normalized instance $n"};dict set instances $normalized $i
 if {[[$i getMaster] isBlock] || [$i isDoNotTouch] || [regexp {^(DFF|SDFF|DFFR|DFFS|DLH|DLL)} [[$i getMaster] getName]]} {dict set protected $n 1}
 foreach it [$i getITerms] {
  if {[[$it getMTerm] getName] in {CK CLK clk clk_i clock}} {set net [$it getNet];if {$net ne "NULL"} {lappend queue $net}}
 }
}
while {[llength $queue]} {
 set net [lindex $queue end];set queue [lrange $queue 0 end-1];set name [$net getName]
 if {[dict exists $visited $name]} {continue};dict set visited $name 1
 foreach it [$net getITerms] {
  if {[[$it getMTerm] getIoType] ne "OUTPUT"} {continue}
  set i [$it getInst];dict set protected [$i getName] 1
  if {[[$i getMaster] isBlock] || [regexp {^(DFF|SDFF|DFFR|DFFS|DLH|DLL)} [[$i getMaster] getName]]} {continue}
  foreach ip [$i getITerms] {if {[[$ip getMTerm] getIoType] eq "INPUT"} {set nn [$ip getNet];if {$nn ne "NULL"} {lappend queue $nn}}}
 }
}
set f [open protected-instances.txt w];puts $f [join [lsort [dict keys $protected]] "\n"];close $f
proc topology {path} {
 set f [open $path w]
 foreach i [[ord::get_db_block] getInsts] {
  set pins {}
  foreach it [$i getITerms] {set net [$it getNet];set nn NULL;if {$net ne "NULL"} {set nn [$net getName]};lappend pins "[[$it getMTerm] getName]=$nn"}
  puts $f [join [list [$i getName] [[$i getMaster] getName] {*}[$i getLocation] [$i getOrient] [join [lsort $pins] |]] "\t"]
 };close $f
}
proc number {path} {
 set f [open $path];set text [string trim [read $f]];close $f
 if {![regexp {([-+]?[0-9]+\.[0-9]+(?:[eE][-+]?[0-9]+)?)\s*$} $text -> n]} {error "Unparsed metric $path: $text"};return $n
}
proc metrics {} {
 global target
 sta::find_timing
 set paths [find_timing_paths -to $target -path_delay max -group_path_count 1 -endpoint_path_count 1]
 if {[llength $paths]!=1} {error "No bounded target path"}
 set ts [get_property [lindex $paths 0] slack]
 report_worst_slack -max -digits 9 > metric-wns.rpt
 report_tns -digits 9 > metric-tns.rpt
 report_worst_slack -min -digits 9 > metric-whs.rpt
 return [list $ts [number metric-wns.rpt] [number metric-tns.rpt] [number metric-whs.rpt] [sta::endpoint_violation_count max] [sta::endpoint_violation_count min] [sta::max_capacitance_violation_count] [sta::max_slew_violation_count] [sta::max_fanout_violation_count]]
}
proc save_metrics {path value} {set f [open $path w];puts $f $value;close $f}
geometry_snapshot geometry-before.tsv
topology source-topology.tsv
save_metrics source-metrics.tsv [metrics]
report_checks -to $target -path_delay max -group_path_count 1 -fields {slew cap fanout input_pin net} -digits 9 > source-target.rpt
set f [open $root/cu/c-v28-combined-size-plan.tsv];gets $f header;set count 0
while {[gets $f line]>=0} {
 lassign [split $line "\t"] name old new;set i [$b findInst $name]
 if {$i eq "NULL" || [[$i getMaster] getName] ne $old || [dict exists $protected $name]} {error "Prequalified 59 source/protection mismatch $name"}
 replace_cell $name $new;incr count
};close $f
if {$count!=59} {error "Expected 59 baseline changes"}
topology topology-before.tsv
set original {};foreach i [$b getInsts] {dict set original [$i getName] [[$i getMaster] getName]}
set baseline [metrics];set best $baseline;save_metrics baseline-metrics.tsv $baseline
report_checks -to $target -path_delay max -group_path_count 3 -endpoint_path_count 3 -fields {slew cap fanout input_pin net} -digits 9 > baseline-target.rpt
set log [open trials.tsv w]
puts $log "trial\tround\tinstance\told\tnew\ttarget_ns\tglobal_wns_ns\tglobal_tns_ns\tglobal_whs_ns\tsetup_count\thold_count\tcap_count\tslew_count\tfanout_count\taccepted";flush $log
set trial 0;set accepted 0;set start [clock seconds]
for {set round 0} {$round<12 && $trial<160 && [clock seconds]-$start<900} {incr round} {
 set todo {};set seen {}
 foreach path [find_timing_paths -to $target -path_delay max -group_path_count 3 -endpoint_path_count 3] {
  foreach pt [get_property $path points] {
   set name [string map [list "\\" ""] [get_full_name [get_property $pt pin]]];set slash [string last / $name]
   if {$slash<0} {continue};set name [string range $name 0 [expr {$slash-1}]]
   if {![dict exists $instances $name]} {continue};set i [dict get $instances $name];set n [$i getName];set old [[$i getMaster] getName]
   if {[dict exists $seen $n] || [dict exists $protected $n] || ![dict exists $equivalents $old]} {continue}
   dict set seen $n 1;lappend todo $n
  }
 }
 if {$round%2==0} {set todo [lreverse $todo]}
 set improved 0
 foreach n $todo {
  set i [$b findInst $n];set initial [[$i getMaster] getName]
  foreach new [dict get $equivalents $initial] {
   if {$trial>=160 || [clock seconds]-$start>=900} {break}
   set old [[$i getMaster] getName];if {$old eq $new} {continue}
   replace_cell $n $new;set now [metrics]
   lassign $best btarget bw bt bh bsc bhc bc bs bf
   lassign $now ntarget nw nt nh nsc nhc nc ns nf
   set keep [expr {$ntarget>$btarget+0.000010 && $nw>=$bw-0.000001 && $nt>=$bt-0.000001 && $nh>=$bh-0.000001 && $nsc<=$bsc && $nhc<=$bhc && $nc<=$bc && $ns<=$bs && $nf<=$bf}]
   incr trial;puts $log [join [concat [list $trial $round $n $old $new] $now [list $keep]] "\t"];flush $log
   if {$keep} {
    set best $now;incr accepted;incr improved;puts "ACCEPT $n $old $new $now";flush stdout
   } else {
    replace_cell $n $old;set restored [metrics]
    for {set j 0} {$j<9} {incr j} {if {abs([lindex $restored $j]-[lindex $best $j])>0.000001} {error "STA restore drift after rejected replacement $n index$j"}}
   }
  }
  if {$trial>=160 || [clock seconds]-$start>=900} {break}
 }
 if {!$improved} {break}
}
close $log
save_metrics final-metrics.tsv [metrics]
set f [open plan.tsv w];puts $f "instance\told\tnew"
foreach i [$b getInsts] {set n [$i getName];set old [dict get $original $n];set new [[$i getMaster] getName];if {$old ne $new} {if {[dict exists $protected $n] || $new ni [dict get $equivalents $old]} {error "Out-of-scope final replacement $n"};puts $f "$n\t$old\t$new"}}
close $f
freeze_selected_c_outputs
geometry_snapshot geometry-after.tsv
exec cmp geometry-before.tsv geometry-after.tsv
topology topology-after.tsv
write_db best.odb
write_verilog best.v
report_checks -to $target -path_delay max -group_path_count 3 -endpoint_path_count 3 -fields {slew cap fanout input_pin net} -digits 9 > final-target.rpt
report_checks -path_delay min_max -group_path_count 20 -digits 9 > final-global-paths.rpt
report_check_types -max_capacitance -max_slew -max_fanout -violators -digits 9 > final-electrical.rpt
report_check_types -recovery -removal -violators -digits 9 > final-async.rpt
report_units
puts "BOUNDED_TARGET_PLANNING_ONLY trials=$trial accepted=$accepted baseline=$baseline final=[metrics]"
puts STATIC_PIN_CAP_AND_CELL_DELAY_SENSITIVITY_WITH_FIXED_QUALIFIED_SOURCE_WIRES_NOT_PHYSICAL_SIGNOFF
