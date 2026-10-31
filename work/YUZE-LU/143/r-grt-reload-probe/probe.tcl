# Read-only diagnostic: can saved GRT data restore its own RC estimate?
set_thread_count 16
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
read_db $::env(BV1_ODB)
read_sdc $::env(BV1_SDC)
source $platform/setRC.tcl
set_routing_layers -signal metal2-metal10 -clock metal2-metal10
if {$::env(BV1_READ_GUIDES)} {read_guides $::env(BV1_GUIDES)}
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
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
report_parasitic_annotation -report_unannotated > annotation.rpt
report_worst_slack -max -digits 9 > timing.rpt
report_worst_slack -min -digits 9 >> timing.rpt
puts "READ_ONLY_DIAGNOSTIC_COMPLETE"
