set_thread_count 8
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.odb
source hook.tcl
set block [ord::get_db_block]
set targets {}
foreach inst [$block getInsts] {
 if {[[$inst getMaster] getName] ne "r_stream_local"} {continue}
 foreach it [$inst getITerms] {set n [$it getNet];if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND}} {dict set targets [$n getName] $n}}
}
set f [open r-access-ripped.tsv w]
foreach name [dict keys $targets] {set n [dict get $targets $name];if {[$n getWire] ne "NULL"} {odb::dbWire_destroy [$n getWire];puts $f $name}}
close $f
pin_access -bottom_routing_layer metal1 -top_routing_layer metal10 -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -min_access_points 1 -verbose 1
puts R_FULL_SPACING_GUARD_STATIC_PIN_ACCESS_PASS_REQUIRES_ACTUAL_ROUTE
