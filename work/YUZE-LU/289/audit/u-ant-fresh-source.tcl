read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(U_LIBS) {read_liberty $lib}
set res $::env(U_RESULTS)
read_db $res/6_final.odb
read_sdc $res/6_final.sdc
read_spef $res/6_final.spef
set_propagated_clock [all_clocks]
sta::find_timing
set bad 0
set f [open fresh-counts.tsv w]
foreach delay {max min} {
 set n [sta::endpoint_violation_count $delay]
 puts $f "$delay\t$n";incr bad $n
}
foreach kind {capacitance slew fanout} {
 set n [sta::max_${kind}_violation_count]
 puts $f "$kind\t$n";incr bad $n
}
close $f
report_worst_slack -max -digits 9 > fresh-setup.rpt
report_worst_slack -min -digits 9 > fresh-hold.rpt
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 9 > fresh-electrical.rpt
report_checks -path_delay min_max -group_path_count 30 -digits 9 > fresh-paths.rpt
if {$bad != 0} {error "Fresh extracted STA/electrical gate failed: $bad violations"}
puts FRESH_TIMING_ELECTRICAL_PASS_NOT_COMPLETE_SIGNOFF
