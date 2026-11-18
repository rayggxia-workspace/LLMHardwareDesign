set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
set res $::env(U_RESULTS)
set old $::env(U_REPAIR_SOURCE)
set_thread_count 8
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(U_LIBS) {read_liberty $lib}
read_db $old/repaired-before-route.odb
read_sdc $old/repaired-before-route.sdc
set_propagated_clock [all_clocks]
source $root/geometry.tcl
file copy $old/flow/results/nangate45/u-overlay-current/base/geometry-before.tsv $res/geometry-before.tsv
set block [ord::get_db_block]
set f [open $old/changed-route-nets.tsv]
set n 0
while {[gets $f name]>=0} {
 set net [$block findNet $name]
 if {$net eq "NULL"} {error "Missing recorded changed net $name"}
 set wire [$net getWire]
 if {$wire ne "NULL"} {odb::dbWire_destroy $wire}
 incr n
}
close $f
puts "RIPPED_RECORDED_CHANGED_NETS $n"
set_routing_layers -signal metal1-metal10 -clock metal1-metal10
set_global_routing_layer_adjustment metal2-metal6 0.20
set_global_routing_layer_adjustment metal7-metal10 0.0
global_route -allow_congestion -verbose -congestion_report_file congestion.rpt
write_db reroute-ready.odb
write_guides reroute.guide
detailed_route -output_drc route-drc.rpt -output_maze maze.log -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5
filler_placement {FILLCELL_X32 FILLCELL_X16 FILLCELL_X8 FILLCELL_X4 FILLCELL_X2 FILLCELL_X1}
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
geometry_snapshot $res/geometry-after.tsv
exec cmp $res/geometry-before.tsv $res/geometry-after.tsv
write_db $res/6_final.odb
write_def $res/6_final.def
write_verilog $res/6_final.v
write_sdc $res/6_final.sdc
extract_parasitics -ext_model_file $platform/rcx_patterns.rules
write_spef $res/6_final.spef
read_spef $res/6_final.spef
report_worst_slack -max -digits 9 > setup.rpt
report_worst_slack -min -digits 9 > hold.rpt
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 9 > electrical.rpt
check_antennas -report_file antenna.rpt
foreach net {VDD VSS} {if {[check_power_grid -net $net] ne "1"} {error "Incomplete $net"}}
puts U_ECO_PHYSICAL_CANDIDATE_NOT_QUALIFIED
