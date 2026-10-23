# Both a successful Tcl call and an explicitly true native result are required.
proc llhd_json_quote {value} {
  return "\"[string map [list "\\" "\\\\" "\"" "\\\"" "\n" "\\n" "\r" "\\r" "\t" "\\t"] $value]\""
}
set block [ord::get_db_block]
set inst [$block findInst u_vec]
if { $inst == "NULL" } { error "Expected macro instance u_vec is absent" }
set file [open ${llhd_pdn_prefix}-macro-pg-iterms.tsv w]
puts $file "instance\tpin\tsignal_type\tnet\tconnected_to_expected_supply"
set pg_count 0
set pg_ok 1
foreach term [$inst getITerms] {
  set pin [$term getMTerm]
  set kind [$pin getSigType]
  if { $kind ni {POWER GROUND} } { continue }
  incr pg_count
  set name [$pin getName]
  set net [$term getNet]
  set net_name "UNCONNECTED"
  if { $net != "NULL" } { set net_name [$net getName] }
  set expected [expr {$kind == "POWER" ? "VDD" : "VSS"}]
  set valid [expr {$net_name == $expected}]
  if { !$valid } { set pg_ok 0 }
  puts $file "u_vec\t$name\t$kind\t$net_name\t$valid"
}
close $file
if { $pg_count != 2 } { set pg_ok 0 }
set failures [expr {!$pg_ok}]
set statuses {}
set codes {}
set values {}
foreach supply {VDD VSS} {
  puts "EXPLICIT CHECK_POWER_GRID $supply BEGIN"
  set code [catch {
    check_power_grid -net $supply -error_file ${llhd_pdn_prefix}-${supply}-errors.rpt
  } value]
  set valid [expr {$code == 0 && [string is boolean -strict $value] && $value}]
  puts "EXPLICIT CHECK_POWER_GRID $supply CATCH_CODE $code RETURNED_VALUE <$value> PASS $valid"
  lappend statuses [expr {$valid ? "true" : "false"}]
  lappend codes $code
  lappend values [llhd_json_quote $value]
  if { !$valid } { set failures 1 }
}
set file [open ${llhd_pdn_prefix}-connectivity.json w]
puts $file "\{"
foreach supply {VDD VSS} i {0 1} {
  puts $file "  \"${supply}_check_power_grid_pass\": [lindex $statuses $i],"
  puts $file "  \"${supply}_catch_code\": [lindex $codes $i],"
  puts $file "  \"${supply}_returned_value\": [lindex $values $i],"
}
puts $file "  \"macro_pg_iterm_count\": $pg_count,"
puts $file "  \"macro_pg_iterms_on_expected_supply_nets\": [expr {$pg_ok ? "true" : "false"}],"
puts $file "  \"acceptance_note\": \"Connectivity only; failed vias are separate. No workload current, IR-drop, EM or PI signoff.\""
puts $file "\}"
close $file
if { $failures } { error "Explicit PG connectivity or macro supply assignment failed; see ${llhd_pdn_prefix}-connectivity.json" }
