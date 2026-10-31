# Diagnostic only: read immutable completed final ODB while full LEC runs.
set_thread_count 16
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
read_db $::env(BV1_ODB)
read_sdc $::env(BV1_SDC)
define_process_corner -ext_model_index 0 X
set_extraction_rules_file $platform/rcx_patterns.rules
extract_parasitics
write_spef diagnostic.spef
read_spef diagnostic.spef
set_propagated_clock [all_clocks]
sta::find_timing
set stream [open summary.tsv w]
puts $stream "diagnostic_only\ttrue"
puts $stream "native_leaf_accepted\tfalse"
puts $stream "setup_checks\t[sta::endpoint_violation_count max]"
puts $stream "hold_checks\t[sta::endpoint_violation_count min]"
foreach kind {capacitance slew fanout} {
 puts $stream "$kind\t[sta::max_${kind}_violation_count]\t[sta::max_${kind}_check_slack]\t[sta::max_${kind}_check_limit]"
}
close $stream
report_worst_slack -max -digits 9 > timing.rpt
report_worst_slack -min -digits 9 >> timing.rpt
report_checks -path_delay min_max -group_path_count 3 -digits 9 -format full_clock_expanded >> timing.rpt
report_check_types -max_capacitance -max_slew -max_fanout -violators -digits 9 -no_line_splits > electrical-violations.rpt
