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

proc snapshot {name} {
    puts "CONTROL_TIMING $name"
    report_worst_slack -max -digits 6
    report_worst_slack -min -digits 6
    report_tns -max -digits 6
    report_checks -path_delay max -group_path_count 3 -digits 6
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
    set replacements [dict create NOR4_X2 NOR4_X4 DFFR_X1 DFFR_X2]
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
        if {[dict exists $replacements $old]} {
            set new [dict get $replacements $old]
            replace_cell $name $new
            if {[[$inst getMaster] getName] ne $new} {
                error "Failed to resize $name from $old to $new"
            }
            puts "CONTROL_ELECTRICAL resized=$name from=$old to=$new"
        }
    }
    close $report
}

snapshot mapped
set utilization 35
if {$::env(CONTROL_TOP) eq "lc_raw16_s_adapter"} {
    set utilization 25
}
initialize_floorplan -utilization $utilization -aspect_ratio 1.0 -core_space 5 \
    -site FreePDK45_38x28_10R_NP_162NW_34O
make_tracks
if {$::env(CONTROL_TOP) eq "lc_raw16_s_adapter"} {
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
if {$violations != 0} {
    global_route -start_incremental
    strengthen_cap_drivers
    detailed_placement
    check_placement
    global_route -end_incremental -guide_file repaired.guide
    estimate_parasitics -global_routing
    set violations [electrical_violations]
}
snapshot routed
puts "CONTROL_ELECTRICAL final=$violations"
report_design_area
write_verilog repaired.v
write_def repaired.def
write_db repaired.odb
