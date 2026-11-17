set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
set source $root/cu/runs/C-v20-native-clock4
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $source/global-candidate.odb
read_sdc $source/route-source.sdc
set_propagated_clock [all_clocks]
source $platform/setRC.tcl
source $root/cu/geometry.tcl
geometry_snapshot geometry-before.tsv
set block [ord::get_db_block]
set_dont_use {TAPCELL_X1 FILLCELL_X1 AOI211_X1 OAI211_X1 OAI221_X4}
set f [open $root/cu/C-outputs.txt]
set selected {}
while {[gets $f port] >= 0} {
    if {$port eq ""} {continue}
    set term [$block findBTerm $port]
    if {$term eq "NULL"} {error "Missing selected output $port"}
    set net [$term getNet]
    set drivers {}
    foreach pin [$net getITerms] {
        if {[[$pin getMTerm] getIoType] eq "OUTPUT"} {lappend drivers [$pin getInst]}
    }
    if {[llength $drivers] != 1} {error "Ambiguous selected driver $port"}
    set driver [lindex $drivers 0]
    if {[[$driver getMaster] getName] ne "BUF_X8"} {error "Expected BUF_X8 on $port"}
    set_dont_touch [get_cells [list [$driver getName]]]
    set_dont_touch [get_nets [list [$net getName]]]
    lappend selected [list $port [$driver getName]]
}
close $f
if {[llength $selected] != 153} {error "Wrong selected output count"}

proc save_reports {prefix} {
    sta::find_timing
    set f [open $prefix-counts.tsv w]
    foreach delay {min max} {puts $f "$delay\t[sta::endpoint_violation_count $delay]"}
    foreach kind {capacitance slew fanout} {puts $f "$kind\t[sta::max_${kind}_violation_count]"}
    close $f
    report_worst_slack -min -digits 9 > $prefix-hold.rpt
    report_worst_slack -max -digits 9 > $prefix-setup.rpt
    report_checks -path_delay min_max -group_path_count 20 -format full_clock_expanded -digits 6 > $prefix-paths.rpt
    report_check_types -max_capacitance -max_slew -max_fanout -violators -digits 9 > $prefix-electrical.rpt
}

set_routing_layers -signal metal2-metal10 -clock metal4-metal10
set_global_routing_layer_adjustment metal2-metal10 0.0
global_route -use_cugr -congestion_iterations 3 -verbose -congestion_report_file before-congestion.rpt
estimate_parasitics -global_routing
save_reports before
repair_design -cap_margin $::env(C_REPAIR_MARGIN) -slew_margin $::env(C_REPAIR_MARGIN)
if {$::env(C_REPAIR_MODE) eq "setup"} {
    repair_timing -setup -setup_margin .030 -repair_tns 100 -verbose
}
detailed_placement
check_placement -verbose
geometry_snapshot geometry-after.tsv
exec cmp geometry-before.tsv geometry-after.tsv
foreach entry $selected {
    lassign $entry port instance
    set net [[$block findBTerm $port] getNet]
    set driver [$block findInst $instance]
    if {$driver eq "NULL" || [[$driver getMaster] getName] ne "BUF_X8"} {error "Selected driver changed $port"}
    if {[[$driver findITerm Z] getNet] ne $net} {error "Selected driver disconnected $port"}
}
write_db repaired-before-global.odb
write_sdc repaired-before-global.sdc
write_verilog repaired-before-global.v
estimate_parasitics -placement
global_route -use_cugr -congestion_iterations 3 -verbose -congestion_report_file after-congestion.rpt
write_guides repaired.guide
write_db repaired-global.odb
estimate_parasitics -global_routing
save_reports after
puts C_GLOBAL_REPAIR_DIAGNOSTIC_REQUIRES_ROUTING_EXTRACTION_AND_ALL_ACCEPTANCE_GATES
