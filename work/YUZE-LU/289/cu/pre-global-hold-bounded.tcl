source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/pre-global-v3.tcl
rename repair_timing cu_original_repair_timing
proc repair_timing {args} {
 if {[lsearch -exact $args -setup]>=0 || [lsearch -exact $args -hold]>=0} {error "Unexpected explicit phase in hold probe"}
 cu_original_repair_timing -setup {*}$args
 set b [ord::get_db_block]
 set before {}
 foreach i [$b getInsts] {dict set before [$i getName] [[$i getMaster] getName]}
 write_db $::env(RESULTS_DIR)/hold-before.odb
 write_sdc $::env(RESULTS_DIR)/hold-before.sdc
 report_checks -path_delay min -group_path_count 100 -format full_clock_expanded -digits 6 > $::env(REPORTS_DIR)/hold-before-paths.rpt
 report_check_types -recovery -removal -violators -verbose -digits 6 > $::env(REPORTS_DIR)/async-before.rpt
 set code [catch {cu_original_repair_timing -hold {*}$args -max_buffer_percent 0.01} reason]
 write_db $::env(RESULTS_DIR)/hold-after-bounded.odb
 write_sdc $::env(RESULTS_DIR)/hold-after-bounded.sdc
 set f [open $::env(RESULTS_DIR)/hold-cell-transforms.tsv w]
 puts $f "kind\tinstance\told_master\tnew_master"
 foreach i [$b getInsts] {
  set name [$i getName];set cell [[$i getMaster] getName]
  if {![dict exists $before $name]} {puts $f "added\t$name\t\t$cell"} elseif {[dict get $before $name] ne $cell} {puts $f "resized\t$name\t[dict get $before $name]\t$cell"}
 }
 close $f
 report_worst_slack -min -digits 6 > $::env(REPORTS_DIR)/hold-after-bounded.rpt
 report_checks -path_delay min -group_path_count 100 -format full_clock_expanded -digits 6 > $::env(REPORTS_DIR)/hold-after-bounded-paths.rpt
 if {$code && $reason ne "RSZ-0060"} {error $reason}
 puts "HOLD_BOUNDED_BUFFER_DIAGNOSTIC_ONLY code=$code reason=$reason"
 exit 0
}
