# Optimize to a positive setup margin, then repair electrical margins again.
# These are optimization targets; the external SDC remains 2.5 ns / 0.5 ns.
set llhd_joint_audit [open [file join $llhd_drive_root joint-repair.tsv] w]
puts $llhd_joint_audit "phase\tsetup_ns\thold_ns"
for {set phase 0} {$phase < $llhd_joint_rounds} {incr phase} {
  set llhd_drive_phase joint${phase}
  estimate_parasitics -global_routing
  repair_timing -setup -setup_margin $llhd_setup_target -repair_tns 100 -skip_gate_cloning -skip_pin_swap -skip_size_down -skip_buffer_removal -skip_buffer_to_inverters -verbose
  estimate_parasitics -global_routing
  repair_timing -hold -hold_margin 0.02 -skip_gate_cloning -skip_pin_swap -skip_size_down -skip_buffer_removal -skip_buffer_to_inverters -verbose
  # Resizer manages routing/parasitic updates during repair_timing. Follow
  # ORFS ordering: start an incremental session only for subsequent DPL.
  global_route -start_incremental
  detailed_placement_helper
  check_placement -verbose
  global_route -end_incremental
  source [file join $llhd_joint_runner targeted_drive.tcl]
  set report [file join $llhd_drive_root joint-slack-${phase}.rpt]
  report_worst_slack -max -digits 9 > $report
  report_worst_slack -min -digits 9 >> $report
  set f [open $report r];set contents [read $f];close $f
  if {![regexp {worst slack max\s+([-+0-9.eE]+)} $contents -> setup] || ![regexp {worst slack min\s+([-+0-9.eE]+)} $contents -> hold]} {error "Missing finite joint repair timing"}
  puts $llhd_joint_audit "$phase\t$setup\t$hold"
  flush $llhd_joint_audit
  puts "JOINT_REPAIR_SLACK phase=$phase setup=$setup hold=$hold"
  if {$setup >= $llhd_setup_accept && $hold >= 0} {break}
}
close $llhd_joint_audit
if {$setup < $llhd_setup_accept || $hold < 0} {error "Joint GRT timing margin insufficient; preserve before DRT"}
