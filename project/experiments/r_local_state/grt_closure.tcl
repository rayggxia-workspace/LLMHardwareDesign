#179 measured new violations after DPL/rerouting, despite repair_timing's zero
#intermediate hold result. Close the loop on actual new global-route RC before
#the normal final metrics/guides/ODB are written. No acceptance rule is changed.
if {![info exists ::r166_grt_closure_installed]} {
 set ::r166_grt_closure_installed 1
 set ::r166_grt_closure_here [file dirname [file normalize [info script]]]
 set ::r166_grt_closure_done 0
 proc r166_grt_observe {stream round} {
  estimate_parasitics -global_routing
  sta::find_timing
  set setup [sta::time_sta_ui [sta::worst_slack_cmd max]]
  set hold [sta::time_sta_ui [sta::worst_slack_cmd min]]
  set sc [sta::endpoint_violation_count max];set hc [sta::endpoint_violation_count min]
  set cap [sta::max_capacitance_violation_count];set slew [sta::max_slew_violation_count]
  puts $stream "$round\t$setup\t$hold\t$sc\t$hc\t$cap\t$slew"
  flush $stream
  puts "R166_GRT_CLOSURE_ROUND=$round; setup=$setup; hold=$hold; setup_count=$sc; hold_count=$hc; cap=$cap; slew=$slew"
  return [list $setup $hold $sc $hc $cap $slew]
 }
 proc r166_grt_close {} {
  set out [open $::r166_grt_closure_here/GRT_CLOSURE.tsv w]
  puts $out "round\tsetup_ns\thold_ns\tsetup_count\thold_count\tcap_count\tslew_count"
  #132's actual GRT->RCX loss was112ps setup/37ps hold. Targets150ps/60ps
  #provide an explicit optimization budget; final original SDC gates stay0.
  for {set round 0} {$round<=6} {incr round} {
   lassign [r166_grt_observe $out $round] setup hold sc hc cap slew
   # Preserve real routed checkpoints for path-level diagnosis of any round.
   write_db $::env(RESULTS_DIR)/r166_grt_closure-round${round}.odb
   write_sdc $::env(RESULTS_DIR)/r166_grt_closure-round${round}.sdc
   report_checks -path_delay min -group_path_count 32 -format full_clock_expanded > $::env(REPORTS_DIR)/r166_closure_${round}_hold.rpt
   report_checks -path_delay max -group_path_count 32 -format full_clock_expanded > $::env(REPORTS_DIR)/r166_closure_${round}_setup.rpt
   if {$sc==0 && $hc==0 && $cap==0 && $slew==0 && $setup>=0.150 && $hold>=0.060} {break}
   if {$round==6} {break}
   global_route -start_incremental
   if {$cap>0 || $slew>0} {repair_design -cap_margin 40 -slew_margin 20 -verbose}
   # Separate the setup optimization goal from the setup guard on hold repair.
   # A positive path below the 150ps setup goal must still be eligible for
   # hold delay when it retains nonnegative setup. Final RCX gates stay exact.
   repair_timing -setup -setup_margin 0.150 -repair_tns 100 -skip_buffer_removal -skip_size_down -verbose
   set hold_args {-hold -setup_margin 0 -hold_margin 0.060 -skip_buffer_removal -skip_size_down -verbose}
   if {[info exists ::r166_hold_batch_iterations]} {
    #192/202 inserted~68k buffers against an unchanged14ps endpoint before
    #hitting RSZ-0060. End a bounded optimizer batch, then legalize and measure
    #real rerouted RC; never treat an iteration limit as an acceptance waiver.
    lappend hold_args -max_iterations $::r166_hold_batch_iterations
   }
   repair_timing {*}$hold_args
   detailed_placement
   check_placement -verbose
   global_connect
   # No -allow_congestion: the native router must converge on actual resources.
   global_route -end_incremental -congestion_report_file $::env(REPORTS_DIR)/r166_closure_${round}.rpt
  }
  close $out
  # Targets are optimizer goals, never substitutes for the exact zero checks.
  # Positive residual margin below target can proceed to independent final RCX.
  if {$sc!=0 || $hc!=0 || $cap!=0 || $slew!=0 || $setup<0 || $hold<0} {
   write_db $::env(RESULTS_DIR)/r166_grt_closure-failed.odb
   error "R166 actual post-placement global-route closure failed; original gates retained"
  }
  puts "R166_GRT_CLOSURE_FINISHED; exact_zero_counts=1; original_final_acceptance_required=1"
 }
 rename report_metrics r166_report_metrics_native
 proc report_metrics {args} {
  if {[llength $args]==2 && [lindex $args 0]==5 && [lindex $args 1] eq "global route" && !$::r166_grt_closure_done} {
   set ::r166_grt_closure_done 1
   r166_grt_close
  }
  r166_report_metrics_native {*}$args
 }
}
