# Sign-off evidence for the native fixture from its own final routed database.
set run $::env(CFJ_OVERLAY_DIR)
set final [file dirname $::env(CFJ_FINAL_ODB)]
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach liberty [split $::env(CFJ_FINAL_LIBS)] {read_liberty $liberty}
read_db $::env(CFJ_FINAL_ODB)
read_sdc $final/6_final.sdc
read_spef $final/6_final.spef
set_propagated_clock [all_clocks]
report_units
write_sdc -digits 9 $run/native-sdc-readback.sdc
sta::find_timing
set receipts [open $run/native-sta-counts.tsv w]
puts $receipts "setup\t[sta::endpoint_violation_count max]"
puts $receipts "hold\t[sta::endpoint_violation_count min]"
foreach kind {capacitance slew fanout} {
  puts $receipts "$kind\t[sta::max_${kind}_violation_count]"
}
close $receipts
check_placement -verbose
foreach net {VDD VSS} {
  if {[check_power_grid -net $net] ne "1"} {error "incomplete $net network"}
}
report_checks -path_delay min_max -group_path_count 20 > $run/native-paths.rpt
report_worst_slack -max -digits 6 > $run/native-setup.rpt
report_worst_slack -min -digits 6 > $run/native-hold.rpt
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 6 > $run/native-electrical.rpt
check_setup -verbose > $run/native-constraints.rpt
