# Optimization-only guard for measured command/reset input hold deficits.
# The real min0.2/max0.8 contract is restored and checked before final output.
if {[llength [info procs repair_timing_helper]] != 1} {error "Native repair helper missing"}
if {[llength [info procs issue143_original_repair_timing_helper]]} {error "Duplicate input hold hook"}
set ::issue143_guard_ports [get_ports {cmd_data* reset}]
set ::issue143_guard_clock [get_clocks core]
if {[llength $::issue143_guard_ports] != 129 || [llength [get_ports reset]] != 1 || [llength [get_ports cmd_data*]] != 128 || [llength $::issue143_guard_clock] != 1} {
 error "R input/clock scope differs from128-bit cmd_data plus reset/core contract"
}
set ::issue143_guard_audit $::env(RESULTS_DIR)/issue143-input-hold-guard.tsv
proc issue143_check_restored_inputs {tag} {
 set path $::env(RESULTS_DIR)/issue143-input-hold-$tag.sdc
 write_sdc $path
 set stream [open $path r]
 set content [read $stream]
 close $stream
 set observed [dict create min [dict create] max [dict create]]
 foreach line [split $content "\n"] {
  if {[regexp {^set_input_delay\s+([-+0-9.eE]+)\s+.*-(min|max).*cmd_data\[([0-9]+)\]} $line -> value kind bit]} {
   if {$bit < 0 || $bit >= 128 || [dict exists $observed $kind $bit]} {error "Duplicate/out-of-scope command input delay"}
   dict set observed $kind $bit $value
  } elseif {[regexp {^set_input_delay\s+([-+0-9.eE]+)\s+.*-(min|max).*\[get_ports \{reset\}\]} $line -> value kind]} {
   if {[dict exists $observed $kind reset]} {error "Duplicate reset input delay"}
   dict set observed $kind reset $value
  }
 }
 foreach {kind expected} {min 0.2 max 0.8} {
  if {[dict size [dict get $observed $kind]] != 129 || ![dict exists $observed $kind reset]} {error "Missing command/reset input timing boundary"}
  dict for {port value} [dict get $observed $kind] {
   if {abs($value-$expected)>1e-8} {error "Input $kind delay not restored for $port: $value"}
  }
 }
 puts "ISSUE143_INPUT_HOLD_SDC_CHECK $tag cmd_data128+reset1 min0.200 max0.800"
}
set_input_delay -min 0.000 -clock $::issue143_guard_clock $::issue143_guard_ports
set_input_delay -min 0.200 -clock $::issue143_guard_clock $::issue143_guard_ports
issue143_check_restored_inputs preflight
set stream [open $::issue143_guard_audit w]
puts $stream "scope\tcmd_data+reset\t129\toptimized_min_ns\t0.000\tsignoff_min_ns\t0.200\tglobal_hold_ns\t0.020"
close $stream
rename repair_timing_helper issue143_original_repair_timing_helper
proc repair_timing_helper {args} {
 set_input_delay -min 0.000 -clock $::issue143_guard_clock $::issue143_guard_ports
 set stream [open $::issue143_guard_audit a]
 puts $stream "entered\t0.000"
 close $stream
 puts "ISSUE143_INPUT_HOLD_GUARD_ENTER cmd_data128+reset1 optimization_min0.000 signoff_min0.200"
 set code [catch {issue143_original_repair_timing_helper {*}$args} value options]
 set_input_delay -min 0.200 -clock $::issue143_guard_clock $::issue143_guard_ports
 issue143_check_restored_inputs restored
 set stream [open $::issue143_guard_audit a]
 puts $stream "restored\t0.200"
 close $stream
 puts "ISSUE143_INPUT_HOLD_GUARD_RESTORED cmd_data128+reset1 signoff_min0.200"
 if {$code} {return -options $options $value}
 return $value
}
