# Isolated diagnostic optimization; no final qualification is issued here.
set_thread_count 16
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
read_db $::env(BV1_ODB)
read_sdc $::env(BV1_SDC)
read_spef $::env(BV1_SPEF)
set_propagated_clock [all_clocks]
set_wire_rc -signal -layer metal3
set_wire_rc -clock -layer metal5
set_dont_use {TAPCELL_X1 FILLCELL_X1 AOI211_X1 OAI211_X1}
proc summarize {name} {
 sta::find_timing
 set stream [open $name.tsv w]
 puts $stream "setup_checks\t[sta::endpoint_violation_count max]"
 puts $stream "hold_checks\t[sta::endpoint_violation_count min]"
 foreach kind {capacitance slew fanout} {
  puts $stream "$kind\t[sta::max_${kind}_violation_count]\t[sta::max_${kind}_check_slack]\t[sta::max_${kind}_check_limit]"
 }
 close $stream
 report_worst_slack -max -digits 9 > $name.rpt
 report_worst_slack -min -digits 9 >> $name.rpt
}
summarize before
if {[sta::endpoint_violation_count max]!=4 || [sta::endpoint_violation_count min]!=325} {error "RC baseline differs from073"}
remove_fillers
set block [ord::get_db_block]
set target [$block findInst wire681011]
if {$target eq "NULL" || [[$target getMaster] getName] ne "BUF_X4"} {error "Cap target differs from073"}
set replacement [[ord::get_db] findMaster BUF_X8]
if {$replacement eq "NULL" || ![$target swapMaster $replacement]} {error "Cap driver resize failed"}
puts "ISSUE143_RESIZE wire681011 BUF_X4 -> [[$target getMaster] getName]"
repair_timing -setup -setup_margin 0.05 -repair_tns 100 -max_passes 20 -max_repairs_per_pass 4 -skip_size_down -verbose
summarize after_setup
repair_timing -hold -hold_margin 0.05 -max_passes 20 -verbose
detailed_placement -incremental
check_placement -verbose
summarize after_repair_estimate
write_db repaired-diagnostic.odb
write_verilog repaired-diagnostic.v -remove_cells {FILLCELL_X1 FILLCELL_X2 FILLCELL_X4 FILLCELL_X8 FILLCELL_X16 FILLCELL_X32 TAPCELL_X1}
puts "DIAGNOSTIC_ONLY: Changed cells invalidate old routed RC; fresh native rerouting, extraction, all final gates and source receipts remain mandatory."
