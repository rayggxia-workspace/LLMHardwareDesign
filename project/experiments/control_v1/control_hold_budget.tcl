# Implementation budget only: no timing exception or acceptance-limit change.
# The 652-bit registered handoff needs real input hold-delay buffers because
# native CTS insertion delay is larger than the fixed 0.2 ns minimum IO delay.
if {[[ord::get_db_block] getName] ne "control_adapter_s"} {error "Hold budget scope mismatch"}
if {[llength [info commands repair_timing_helper]]!=1} {error "Missing native repair helper"}
rename repair_timing_helper issue162_native_repair_timing_helper
proc repair_timing_helper {args} {
 puts "ISSUE162_HOLD_BUFFER_BUDGET=100; unchanged SDC, native checks and final acceptance"
 issue162_native_repair_timing_helper {*}$args -max_buffer_percent 100
}
