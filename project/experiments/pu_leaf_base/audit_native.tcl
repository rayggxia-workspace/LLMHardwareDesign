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
set bindings [open "$out/m10-bindings.tsv" w]
puts $bindings "port\tdirection\tnet\tinternal_driver_count\tinternal_sink_count\tinternal_terminals"
foreach terminal [$block getBTerms] {
    foreach pin [$terminal getBPins] {
        foreach box [$pin getBoxes] {
            if {[[$box getTechLayer] getName] eq "metal10"} {
                set name [$terminal getName]
                puts $f "$name\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
                if {![regexp {^(m_to_g_|g_from_m_|n_to_e_|e_direct_a_)} $name]} {continue}
                set net [$terminal getNet]
                if {$net eq "NULL"} {error "unconnected late endpoint $name"}
                set sources 0
                set sinks 0
                set connections {}
                foreach term [$net getITerms] {
                    set mterm [$term getMTerm]
                    set dir [$mterm getIoType]
                    if {$dir eq "OUTPUT"} {incr sources}
                    if {$dir eq "INPUT"} {incr sinks}
                    lappend connections "[[$term getInst] getName]/[$mterm getName]:$dir"
                }
                set dir [$terminal getIoType]
                if {$dir eq "OUTPUT" && $sources != 1 || $dir eq "INPUT" && ($sinks < 1 || $sources != 0)} {
                    error "invalid late endpoint connectivity $name $dir $sources $sinks"
                }
                puts $bindings "$name\t$dir\t[$net getName]\t$sources\t$sinks\t[join [lsort $connections] { }]"
            }
        }
    }
}
close $f
close $bindings
set leaves [open "$out/leaf-instances.tsv" w]
puts $leaves "instance\tmaster\tx_dbu\ty_dbu\torientation\twidth_dbu\theight_dbu"
foreach inst [$block getInsts] {
    set master [$inst getMaster]
    if {![$master isBlock]} {continue}
    lassign [$inst getLocation] x y
    puts $leaves "[$inst getName]\t[$master getName]\t$x\t$y\t[$inst getOrient]\t[$master getWidth]\t[$master getHeight]"
}
close $leaves
puts "=== EXTRACTED SETUP AND HOLD ==="
report_worst_slack -max -digits 6
report_worst_slack -min -digits 6
report_tns -max -digits 6
report_tns -min -digits 6
puts "=== CRITICAL HOLD PATHS ==="
report_checks -path_delay min -group_path_count 5 -digits 6 -format full_clock_expanded
puts "=== CRITICAL SETUP PATHS ==="
report_checks -path_delay max -group_path_count 5 -digits 6 -format full_clock_expanded
set endpoint_file [open "$out/hold-endpoints.tsv" w]
puts $endpoint_file "capture_pin\tslack_ns"
set captured [dict create]
set hold_paths [find_timing_paths -path_delay min -slack_max 0.035 -group_path_count 20000 -endpoint_path_count 1]
if {[llength $hold_paths] >= 20000} {error "hold endpoint report reached its search limit"}
foreach path $hold_paths {
    set endpoint [get_full_name [get_property $path endpoint]]
    set slack [get_property $path slack]
    if {![dict exists $captured $endpoint] || $slack < [dict get $captured $endpoint]} {
        dict set captured $endpoint $slack
    }
}
dict for {endpoint slack} $captured {puts $endpoint_file "$endpoint\t$slack"}
close $endpoint_file
puts "=== ELECTRICAL VIOLATIONS ==="
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 6
puts "=== CONSTRAINT AUDIT ==="
if {![check_setup -verbose]} {error "Native timing constraints are incomplete"}
puts "=== POWER CONNECTIVITY ==="
if {![design_is_routed -verbose]} {error "Design has unrouted signal nets"}
foreach supply {VDD VSS} {
    if {[check_power_grid -net $supply -error_file "$out/audit-$supply.rpt"] ne "1"} {
        error "Disconnected $supply"
    }
}
