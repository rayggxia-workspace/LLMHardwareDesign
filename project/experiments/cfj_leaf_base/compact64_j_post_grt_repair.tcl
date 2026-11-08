# Use the previous extracted candidate as an implementation hint, never as
# final evidence. The new final SPEF, original limits and complete DRC decide.
if {![info exists cfj_repair_reference] || ![file isfile $cfj_repair_reference]} {
  error "Missing pinned extracted repair reference"
}
global_route -start_incremental -allow_congestion
read_spef $cfj_repair_reference
set_propagated_clock [all_clocks]
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 6 \
  > $::env(REPORTS_DIR)/post-grt-reference-electrical.rpt
repair_design -slew_margin 65 -cap_margin 50 -verbose
repair_timing -hold -hold_margin 0.050 -max_buffer_percent 2 -verbose
detailed_placement_helper
check_placement -verbose
global_route -end_incremental -allow_congestion \
  -congestion_report_file $::env(REPORTS_DIR)/post-grt-extracted-repair-congestion.rpt
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
