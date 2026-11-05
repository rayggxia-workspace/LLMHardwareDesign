# Search/implementation resource budget after retained RSZ-0060 failures.
# No SDC exception, clock change, slack waiver or qualification is introduced.
set issue162_r256_hold_top [[ord::get_db_block] getName]
if {$issue162_r256_hold_top ni {control_adapter_r control_s_arbiter_r7}} {error "R256 hold budget scope mismatch"}
if {[llength [info commands repair_timing_helper]]!=1} {error "Missing original repair helper"}
rename repair_timing_helper issue162_r256_original_repair_timing_helper
proc repair_timing_helper {args} {
 puts "ISSUE162_R256_HOLD_BUFFER_BUDGET=100; original SDC and all final gates unchanged"
 issue162_r256_original_repair_timing_helper {*}$args -max_buffer_percent 100
}
