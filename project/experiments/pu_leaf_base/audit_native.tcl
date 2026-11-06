# Native physical audit and exact upper endpoint export.
read_liberty $::env(PU_STD_LIB)
foreach lib [glob -directory $::env(PU_CANDIDATE) *.lib] {read_liberty $lib}
read_db $::env(PU_FINAL_ODB)
read_sdc $::env(PU_FINAL_SDC)
read_spef $::env(PU_FINAL_SPEF)
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
set out $::env(PU_CANDIDATE)
set f [open "$out/m10-pins.tsv" w]
foreach terminal [$block getBTerms] {
    foreach pin [$terminal getBPins] {
        foreach box [$pin getBoxes] {
            if {[[$box getTechLayer] getName] eq "metal10"} {
                puts $f "[$terminal getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
            }
        }
    }
}
close $f
puts "=== EXTRACTED SETUP AND HOLD ==="
report_worst_slack -max -digits 6
report_worst_slack -min -digits 6
report_tns -max -digits 6
report_tns -min -digits 6
puts "=== CRITICAL HOLD PATHS ==="
report_checks -path_delay min -group_path_count 5 -digits 6 -format full_clock_expanded
puts "=== ELECTRICAL VIOLATIONS ==="
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 6
puts "=== CONSTRAINT AUDIT ==="
check_setup -verbose
puts "=== POWER CONNECTIVITY ==="
if {![design_is_routed -verbose]} {error "Design has unrouted signal nets"}
foreach supply {VDD VSS} {
    if {[check_power_grid -net $supply -error_file "$out/audit-$supply.rpt"] ne "1"} {
        error "Disconnected $supply"
    }
}
