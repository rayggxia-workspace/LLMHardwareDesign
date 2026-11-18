set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $root/audit/C-v28-nine-net-normalization-v1/reextract-encoder/before.odb
read_sdc $root/cu/runs/C-v28-actual-i8-h50/flow/results/nangate45/c-overlay-current/base/6_final.sdc
set_propagated_clock [all_clocks]
source $platform/setRC.tcl
source $root/cu/geometry.tcl
source $root/cu/c-freeze-outputs-v1.tcl
freeze_selected_c_outputs
if {![llength [info commands set_nets_to_route]]} {error "Installed build lacks specific-net routing"}
set f [open installed-routing-api.tcl w]
puts $f [info body set_nets_to_route]
puts $f [info body set_routing_layers]
close $f
set block [ord::get_db_block]
set target [$block findNet net73798]
if {$target eq "NULL" || [$target getSigType] ne "CLOCK"} {error "Unexpected clock net"}
set endpoints {}
foreach it [$target getITerms] {lappend endpoints [list [[$it getInst] getName] [[$it getMTerm] getName]]}
if {[lsort $endpoints] ne [lsort {{wire73799 Z} {wire73798 A}}]} {error "Clock topology differs"}
set coordinates {}
foreach inst [$block getInsts] {dict set coordinates [$inst getName] [list [$inst getLocation] [$inst getOrient] [[$inst getMaster] getName]]}
geometry_snapshot geometry-before.tsv
write_verilog logic-before.v
set wire [$target getWire]
if {$wire eq "NULL"} {error "Expected original routed clock"}
odb::dbWire_destroy $wire
set f [open explicitly-ripped.tsv w];puts $f net73798;close $f
foreach guide_net [$block getNets] {foreach guide [$guide_net getGuides] {odb::dbGuide_destroy $guide}}
set selected {net73798}
set byname {}
foreach inst [$block getInsts] {dict set byname [string map [list "\\" ""] [$inst getName]] $inst}
foreach spec {{{services.store.leaf} {req_data[74]}} {{services.engine[2].genblk1.recurrent.leaf.leaf} cmd_ready} {{services.engine[0].element.arithmetic.leaf} {in_data[105]}}} {
 lassign $spec iname term
 if {![dict exists $byname $iname]} {error "Missing recovery macro $iname"}
 set it [[dict get $byname $iname] findITerm $term]
 if {$it eq "NULL"} {error "Missing recovery pin"}
 set n [$it getNet]
 if {$n eq "NULL" || [$n getSigType] ne "SIGNAL"} {error "Unexpected recovery net"}
 lappend selected [$n getName]
 set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w}
}
set f [open selected-scope.tsv w];puts $f $selected;close $f
set minimum $::env(CLOCK_MIN_LAYER)
if {$minimum ni {4 7 9}} {error "Unexpected clock layer experiment"}
set_routing_layers -signal metal2-metal10 -clock metal${minimum}-metal10
set_global_routing_layer_adjustment metal2-metal10 0.0
foreach selected_name $selected {set exact_net [$block findNet $selected_name];if {$exact_net eq "NULL"} {error "Missing selected literal DB net"};grt::add_net_to_route $exact_net}
global_route -congestion_iterations 20 -verbose
write_guides route.guide
set f [open route.guide];set guides [read $f];close $f
set names {}
foreach line [split $guides "\n"] {
 set line [string trim $line]
 if {$line eq "" || $line in {( )} || [regexp {^[-+0-9.eE]+\s+[-+0-9.eE]+\s+[-+0-9.eE]+\s+[-+0-9.eE]+\s+metal[0-9]+$} $line]} {continue}
 lappend names $line
}
if {[lsort -unique $names] ne [lsort -unique $selected]} {error "Unexpected global-guide scope: [llength $names] headers"}
write_db global.odb
pin_access -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -verbose 1
detailed_route -no_pin_access -output_drc route-drc.rpt -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -droute_end_iter 20 -drc_report_iter_step 5 -verbose 1
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {![dict exists $coordinates $name] || [dict get $coordinates $name] ne [list [$inst getLocation] [$inst getOrient] [[$inst getMaster] getName]]} {error "Unexpected cell/master movement $name"}
}
freeze_selected_c_outputs
geometry_snapshot geometry-after.tsv
exec cmp geometry-before.tsv geometry-after.tsv
set res $::env(U_RESULTS)
write_db $res/6_final.odb
write_def $res/6_final.def
write_verilog $res/6_final.v
exec cmp logic-before.v $res/6_final.v
file copy $root/cu/runs/C-v28-actual-i8-h50/flow/results/nangate45/c-overlay-current/base/6_final.sdc $res/6_final.sdc
extract_parasitics -ext_model_file $platform/rcx_patterns.rules
write_spef $res/6_final.spef
write_db $res/6_post_rcx.odb
write_def $res/6_post_rcx.def
puts ACTUAL_CLOCK_WIRE_LAYER_DIAGNOSTIC_NO_CLOCK_OR_IO_CONSTRAINT_CHANGE
