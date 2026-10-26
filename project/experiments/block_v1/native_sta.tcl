# Read-only independent STA. A fresh process reads actual ODB/SDC/SPEF.
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
set_thread_count $::env(OMP_NUM_THREADS)
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
read_db $::env(BV1_ODB)
read_sdc $::env(BV1_SDC)
report_units
read_spef $::env(BV1_SPEF)
set_propagated_clock [all_clocks]
sta::find_timing
write_sdc constraints-readback.sdc
report_parasitic_annotation -report_unannotated > annotation.rpt
set stream [open endpoints.tsv w]
foreach pin [sta::endpoints] {
  set maximum [get_property $pin slack_max]
  set minimum [get_property $pin slack_min]
  set unused_fanout -1
  if {$maximum in {INF -INF} && $minimum in {INF -INF}} {
    set unused_fanout 0
    foreach reached [get_fanout -from [list $pin] -flat -pin_levels 2 -trace_arcs all] {
      if {$reached ne $pin} {incr unused_fanout}
    }
  }
  puts $stream "[get_full_name $pin]\t$maximum\t$minimum\t[get_property $pin is_port]\t[string tolower [get_property $pin direction]]\t$unused_fanout"
}
close $stream
set stream [open timing-summary.tsv w]
puts $stream "setup_checks\t[sta::endpoint_violation_count max]"
puts $stream "hold_checks\t[sta::endpoint_violation_count min]"
puts $stream "check_setup\t[check_setup -verbose]"
puts $stream "time_unit_seconds\t[sta::time_ui_sta 1]"
puts $stream "capacitance_unit_farads\t[sta::capacitance_ui_sta 1]"
foreach clock [all_clocks] {
  puts $stream "clock\t[get_full_name $clock]\t[get_property $clock is_propagated]"
}
foreach kind {capacitance slew fanout} {
  puts $stream "$kind\t[sta::max_${kind}_violation_count]\t[sta::max_${kind}_check_slack]\t[sta::max_${kind}_check_limit]"
}
close $stream
report_worst_slack -max -digits 9 > timing.rpt
report_worst_slack -min -digits 9 >> timing.rpt
report_tns -max -digits 9 >> timing.rpt
report_tns -min -digits 9 >> timing.rpt
report_checks -path_delay min_max -group_path_count 10 -digits 9 -format full_clock_expanded >> timing.rpt
# Delay checks are covered by the complete endpoint table and native counts.
report_check_types -max_capacitance -max_slew -max_fanout -violators -digits 9 -no_line_splits > electrical-violations.rpt
report_check_types -max_capacitance -max_slew -max_fanout -max_count 3 -digits 9 -no_line_splits > electrical-worst.rpt
