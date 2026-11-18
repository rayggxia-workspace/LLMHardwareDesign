set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db global-candidate.odb
read_sdc route-source.sdc
set_propagated_clock [all_clocks]
source $platform/setRC.tcl
source $root/geometry.tcl
geometry_snapshot geometry-before-route.tsv
set_routing_layers -signal metal2-metal10 -clock metal$::env(CU_CLOCK_MIN)-metal10
read_guides route.guide
detailed_route -output_drc route-drc.rpt -output_maze maze.log -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5
filler_placement {FILLCELL_X32 FILLCELL_X16 FILLCELL_X8 FILLCELL_X4 FILLCELL_X2 FILLCELL_X1}
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
geometry_snapshot geometry-after-route.tsv
exec cmp geometry-before-route.tsv geometry-after-route.tsv
set res $::env(CU_RESULTS)
write_db $res/6_final.odb
write_def $res/6_final.def
write_verilog $res/6_final.v
write_sdc $res/6_final.sdc
if {[file size route-drc.rpt] != 0} {error "Native DRC failed; saved geometry is diagnostic only"}
extract_parasitics -ext_model_file $platform/rcx_patterns.rules
write_spef $res/6_final.spef
puts NATIVE_CANDIDATE_REQUIRES_FRESH_STA_PG_AND_FULL_DECK