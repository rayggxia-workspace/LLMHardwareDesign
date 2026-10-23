# Strict native connectivity and every actual macro supply assignment.
set llhd_b [ord::get_db_block]
set llhd_pg_count 0
foreach llhd_name $llhd_macro_instances {
  set inst [$llhd_b findInst $llhd_name]
  if {$inst eq "NULL"} {error "Missing macro $llhd_name"}
  set count 0
  foreach term [$inst getITerms] {
    set kind [[$term getMTerm] getSigType]
    if {$kind ni {POWER GROUND}} {continue}
    incr count
    set expected [expr {$kind eq "POWER" ? "VDD" : "VSS"}]
    set net [$term getNet]
    if {$net eq "NULL" || [$net getName] ne $expected} {error "Incorrect supply on $llhd_name"}
  }
  if {$count != 2} {error "Expected VDD and VSS on $llhd_name"}
  incr llhd_pg_count $count
}
set llhd_f [open [file join $::env(LLHD_ATTEMPT) strict-pg.json] w]
puts $llhd_f "\{\"macro_pg_iterm_count\": $llhd_pg_count,"
foreach supply {VDD VSS} {
  set code [catch {check_power_grid -net $supply -error_file [file join $::env(LLHD_ATTEMPT) $supply-errors.rpt]} value]
  set valid [expr {$code == 0 && [string is boolean -strict $value] && $value}]
  puts "STRICT_PG $supply code=$code return=<$value> pass=$valid"
  puts $llhd_f "\"${supply}_pass\": [expr {$valid ? {true} : {false}}],"
  if {!$valid} {close $llhd_f; error "Strict PG failed on $supply"}
}
puts $llhd_f "\"passed\": true\}"
close $llhd_f
