# Read-only diagnosis at the actual completed S GRT checkpoint. Intentionally
# stop before detailed routing; this is never a candidate acceptance gate.
global_route -start_incremental
global_route -end_incremental
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
sta::find_timing
report_checks -path_delay min -slack_max 0 -group_path_count 24 -endpoint_path_count 1 -digits 12 > $::env(RESULTS_DIR)/feed-s-short-paths.rpt
report_checks -from [get_ports reset] -path_delay max -group_path_count 8 -digits 12 > $::env(RESULTS_DIR)/feed-s-reset-setup.rpt
report_check_types -max_capacitance -max_slew -violators -digits 12 > $::env(RESULTS_DIR)/feed-s-drivers.rpt
set block [ord::get_db_block]
set f [open $::env(RESULTS_DIR)/feed-s-driver-pins.tsv w]
foreach name {wire42991 wire42863 input175} {
  set inst [$block findInst $name]
  if {$inst eq "NULL"} {error "Measured S driver missing"}
  puts $f "instance\t$name\t[[$inst getMaster] getName]"
  foreach term [$inst getITerms] {
    set net [$term getNet]
    if {$net eq "NULL"} {continue}
    if {[[$term getMTerm] getSigType] in {POWER GROUND}} {continue}
    puts $f "pin\t$name/[[$term getMTerm] getName]\t[$net getName]"
    foreach endpoint [$net getITerms] {
      puts $f "endpoint\t[[$endpoint getInst] getName]/[[$endpoint getMTerm] getName]\t[[[$endpoint getInst] getMaster] getName]\t[[$endpoint getMTerm] getIoType]"
    }
  }
}
close $f
error "Read-only S GRT diagnosis complete; intentionally no detailed-route candidate"
