# S-only addition to the independent, propagated-clock final STA.
# Missing library clock checks or an unclocked bank fail closed in Python.
set sram_cells [get_cells -hierarchical -filter {ref_name == s_sram_256x128_freepdk45}]
if {[llength $sram_cells] != 4} {error "Expected four actual SRAM instances"}
set sram_core [get_clocks core]
if {[llength $sram_core] != 1} {error "Missing unique core clock"}
set sram_stream [open sram-clocks.tsv w]
foreach sram_cell $sram_cells {
  set sram_pins [get_pins -of_objects $sram_cell -filter {lib_pin_name == clk0}]
  if {[llength $sram_pins] != 1} {error "Missing unique SRAM clock pin"}
  set sram_pin [lindex $sram_pins 0]
  set sram_clocks [get_property $sram_pin clocks]
  if {[llength $sram_clocks] != 1} {error "SRAM pin has no unique clock"}
  set sram_clock [lindex $sram_clocks 0]
  if {[get_full_name $sram_clock] ne "core" ||
      [get_property $sram_clock period] != [get_property $sram_core period] ||
      ![get_property $sram_clock is_propagated]} {error "Incorrect SRAM clock"}
  puts $sram_stream "[get_full_name $sram_pin]\t[get_full_name $sram_clock]\t[get_property $sram_clock period]\t[get_property $sram_clock is_propagated]"
}
close $sram_stream
report_check_types -min_period -max_count 10000000 -digits 9 -no_line_splits > sram-period.rpt
report_check_types -min_pulse_width -max_count 10000000 -digits 9 -no_line_splits > sram-pulse.rpt
report_check_types -min_period -min_pulse_width -violators -digits 9 -no_line_splits > sram-clock-violations.rpt
