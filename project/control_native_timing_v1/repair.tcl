# Standalone, single-clock pre-CTS timing repair. The target period is fixed.
set_thread_count 1
set platform $::env(CONTROL_N45)
read_lef $platform/lef/NangateOpenCellLibrary.tech.lef
read_lef $platform/lef/NangateOpenCellLibrary.macro.mod.lef
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
read_verilog tied.v
link_design $::env(CONTROL_TOP)
set sdc [open repaired.sdc w]
puts $sdc [format {create_clock -name core -period 3.333333333 [get_ports {%s}]} $::env(CONTROL_CLK)]
close $sdc
source repaired.sdc
set data_inputs [lsearch -all -inline -not -exact [all_inputs] [lindex [get_ports $::env(CONTROL_CLK)] 0]]
set data_outputs [all_outputs]
set_input_delay -clock core -max 0.5 $data_inputs
set_input_delay -clock core -min 0.05 $data_inputs
set_output_delay -clock core -max 0.5 $data_outputs
set_output_delay -clock core -min 0.05 $data_outputs
set_input_transition 0.05 $data_inputs
set_load 5 $data_outputs
set_clock_uncertainty -setup 0.05 [get_clocks core]
set_clock_uncertainty -hold 0.02 [get_clocks core]
report_units
puts "CONTROL_COVERAGE initial"
check_setup -verbose


proc snapshot {name} {
    puts "CONTROL_TIMING $name"
    report_worst_slack -max -digits 6
    report_worst_slack -min -digits 6
    report_tns -max -digits 6
    report_checks -path_delay max -group_path_count 3 -digits 6
    report_checks -path_delay min -group_path_count 3 -digits 6
}

proc electrical_violations {} {
    report_check_types -max_slew -max_capacitance -violators > electrical.rpt
    set report [open electrical.rpt r]
    set violations [regexp -all {\(VIOLATED\)} [read $report]]
    close $report
    return $violations
}

proc strengthen_cap_drivers {} {
    set report [open electrical.rpt r]
    set cap_section 0
    set replacements [dict create NOR2_X1 NOR2_X2 NOR4_X2 NOR4_X4 DFFR_X1 DFFR_X2 XOR2_X1 XOR2_X2 XNOR2_X1 XNOR2_X2]
    set resized 0
    while {[gets $report line] >= 0} {
        if {[string match "max *" $line]} {
            set cap_section [string equal $line "max capacitance"]
        }
        if {!$cap_section || ![regexp {^([^/[:space:]]+)/[^[:space:]]+.*\(VIOLATED\)$} $line -> name]} {
            continue
        }
        set inst [[ord::get_db_block] findInst $name]
        if {$inst eq "NULL"} {
            error "Could not find violating driver $name"
        }
        set old [[$inst getMaster] getName]
        if {[regexp {^(.*)_X([0-9]+)$} $old -> family drive] && $drive < 32} {
            set new ${family}_X[expr {$drive * 2}]
            if {[[ord::get_db] findMaster $new] eq "NULL"} { continue }
            replace_cell $name $new
            if {[[$inst getMaster] getName] ne $new} {
                error "Failed to resize $name from $old to $new"
            }
            incr resized
            puts "CONTROL_ELECTRICAL resized=$name from=$old to=$new"
        }
    }
    close $report
    return $resized
}

snapshot mapped
set top $::env(CONTROL_TOP)
set wide_native [expr {$top in {lc_u_rms_adapter lc_j_lease_adapter lc_c_state_adapter}}]
if {$top eq "two_local_link"} {
    initialize_floorplan -die_area {0 0 160 160} -core_area {5 5 155 155} -site FreePDK45_38x28_10R_NP_162NW_34O
} elseif {$wide_native} {
    # Fixed perimeter for wide logical service and macro ports in standalone STA.
    initialize_floorplan -die_area {0 0 200 200} -core_area {5 5 195 195}         -site FreePDK45_38x28_10R_NP_162NW_34O
} elseif {$top eq "cohort_reset_controller"} {
    initialize_floorplan -die_area {0 0 100 100} -core_area {5 5 95 95}         -site FreePDK45_38x28_10R_NP_162NW_34O
} elseif {$top in {lc_m_dot_store_adapter lc_f_store_adapter p_stored_ack_guard}} {
    # Reserve perimeter for the service descriptor and the M, G, S buses.
    initialize_floorplan -die_area {0 0 145 145} -core_area {5 5 140 140} \
        -site FreePDK45_38x28_10R_NP_162NW_34O
} else {
    set utilization [expr {$top eq "lc_raw16_s_adapter" ? 25 : 35}]
    initialize_floorplan -utilization $utilization -aspect_ratio 1.0 -core_space 5 \
        -site FreePDK45_38x28_10R_NP_162NW_34O
}
make_tracks
if {$top eq "two_local_link" || $wide_native || $top in {lc_raw16_s_adapter lc_m_dot_store_adapter lc_f_store_adapter p_stored_ack_guard cohort_reset_controller}} {
    place_pins -hor_layers {metal3 metal5} -ver_layers {metal2 metal4}
} else {
    place_pins -hor_layers metal3 -ver_layers metal2
}
set_wire_rc -signal -layer metal3
set_wire_rc -clock -layer metal5
global_placement -density 0.48
estimate_parasitics -placement
snapshot placed
repair_design -max_utilization 65 -slew_margin 10 -cap_margin 10
detailed_placement
estimate_parasitics -placement
snapshot buffered
repair_timing -setup -setup_margin 0.05 -max_utilization 65 -max_passes 20
detailed_placement
check_placement
estimate_parasitics -placement
snapshot repaired
set_routing_layers -signal metal2-metal8
global_route -congestion_iterations 30 -guide_file repaired.guide
estimate_parasitics -global_routing
snapshot routed_initial
# Preserve recovery/removal checks on asynchronous reset. Repair minimum
# paths with delay cells/buffers instead of suppressing those checks.
for {set hold_pass 1} {$hold_pass <= 4} {incr hold_pass} {
    puts "CONTROL_HOLD pass=$hold_pass"
    global_route -start_incremental
    repair_timing -hold -hold_margin 0.03 -max_buffer_percent 50 -max_utilization 65 -max_passes 20
    repair_design -max_utilization 65 -slew_margin 25 -cap_margin 25
    set violations [electrical_violations]
    if {$violations != 0} { strengthen_cap_drivers }
    detailed_placement
    check_placement
    global_route -end_incremental -guide_file repaired.guide
    estimate_parasitics -global_routing
}
set violations [electrical_violations]
for {set pass 1} {$pass <= 3 && $violations != 0} {incr pass} {
    puts "CONTROL_ELECTRICAL pass=$pass violations_before=$violations"
    global_route -start_incremental
    repair_design -max_utilization 65 -slew_margin 25 -cap_margin 25
    detailed_placement
    check_placement
    global_route -end_incremental -guide_file repaired.guide
    estimate_parasitics -global_routing
    set violations [electrical_violations]
}
for {set pass 1} {$pass <= 3 && $violations != 0} {incr pass} {
    global_route -start_incremental
    set resized [strengthen_cap_drivers]
    detailed_placement
    check_placement
    global_route -end_incremental -guide_file repaired.guide
    estimate_parasitics -global_routing
    set violations [electrical_violations]
    if {$resized == 0} { break }
}
snapshot routed
puts "CONTROL_COVERAGE final"
check_setup -verbose
puts "CONTROL_UNCONSTRAINED"
report_checks -unconstrained -group_path_count 20
write_sdc full-budget.sdc
puts "CONTROL_ELECTRICAL final=$violations"
report_design_area
write_verilog repaired.v
write_def repaired.def
write_db repaired.odb
