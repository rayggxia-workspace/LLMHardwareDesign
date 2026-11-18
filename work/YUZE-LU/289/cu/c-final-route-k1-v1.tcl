set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $::env(C_BOUNDED_SOURCE)/regenerated-ap.odb
read_sdc $::env(C_ECO_SOURCE_SDC)
set_propagated_clock [all_clocks]
source $platform/setRC.tcl
source $root/geometry.tcl
source $root/c-freeze-outputs-v1.tcl
set_routing_layers -signal metal2-metal10 -clock metal4-metal10
read_guides $::env(C_BOUNDED_SOURCE)/route.guide
detailed_route -no_pin_access -output_drc route-drc.rpt -output_maze maze.log -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -or_seed $::env(C_ROUTE_SEED) -or_k 1 -droute_end_iter 32 -verbose 1 -drc_report_iter_step 5
filler_placement {FILLCELL_X32 FILLCELL_X16 FILLCELL_X8 FILLCELL_X4 FILLCELL_X2 FILLCELL_X1}
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
freeze_selected_c_outputs
geometry_snapshot geometry-after-route.tsv
exec cmp geometry-original.tsv geometry-after-route.tsv
set res $::env(CU_RESULTS)
write_db $res/6_final.odb
write_def $res/6_final.def
write_verilog $res/6_final.v
file copy -force $::env(C_ECO_SOURCE_SDC) $res/6_final.sdc
set f [open native-result.txt w]
puts $f "native_report_bytes=[file size route-drc.rpt]"
puts $f "accepted=false_pending_all_gates"
close $f
# Extract also for failed-route diagnosis; acceptance never follows process exit.
extract_parasitics -ext_model_file $platform/rcx_patterns.rules
write_spef $res/6_final.spef
write_db $res/6_post_rcx.odb
write_def $res/6_post_rcx.def
puts JOINT_PHYSICAL_CANDIDATE_REQUIRES_FRESH_STA_GEOMETRY_RC_CONSISTENCY_LEC_PG_FULL_GDS
