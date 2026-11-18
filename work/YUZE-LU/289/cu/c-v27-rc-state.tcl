set_thread_count 8
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(U_LIBS) {read_liberty $lib}
read_db $::env(U_RESULTS)/6_final.odb
read_sdc $::env(U_RESULTS)/6_final.sdc
read_spef $::env(U_RESULTS)/6_final.spef
set_propagated_clock [all_clocks]
proc snapshot {name} {
 sta::find_timing
 set f [open rc-state.tsv a]
 puts $f "$name\t[sta::endpoint_violation_count max]\t[sta::endpoint_violation_count min]\t[sta::max_capacitance_violation_count]\t[sta::max_slew_violation_count]"
 close $f
 report_worst_slack -max -digits 9 > ${name}-setup.rpt
}
snapshot fresh
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
snapshot after_setRC
remove_fillers
snapshot after_remove_fillers
read_spef $::env(U_RESULTS)/6_final.spef
snapshot after_reread_spef
puts READ_ONLY_SOURCE_DIAGNOSTIC_COMPLETE
