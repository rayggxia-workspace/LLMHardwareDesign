# Native routing support probe ONLY; no six-block or common-base claim.
read_lef $::env(PINXY_TECH)
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_verilog $::env(PINXY_VERILOG)
link_design upper_probe
initialize_floorplan -die_area {0 0 100 100} -core_area {0 0 100 100} -site FreePDK45_38x28_10R_NP_162NW_34O
make_tracks
foreach {pin x y} {a 19.295 19.27 y 80.095 80.07 b 19.295 80.07 z 80.095 19.27} {
  place_pin -pin_name $pin -layer metal10 -location [list $x $y] -pin_size {.8 .8}
}
source $::env(PINXY_RC)
report_units
set_routing_layers -signal metal11-metal12 -clock metal11-metal12
write_db $::env(PINXY_OUT)/before.odb
global_route -guide_file $::env(PINXY_OUT)/route.guide
detailed_route -output_drc $::env(PINXY_OUT)/route.drc -verbose 1
write_db $::env(PINXY_OUT)/routed.odb
source $::env(PINXY_DRIVER)/export_access.tcl
drt::check_drc -output_file $::env(PINXY_OUT)/native.drc
set f [open $::env(PINXY_OUT)/layers.tsv w]
puts $f "layer\ttype\tlevel\twidth\tspacing\tpitchx\tpitchy\tdirection"
foreach l [[ord::get_db_tech] getLayers] {
  puts $f [join [list [$l getName] [$l getType] [$l getRoutingLevel] [$l getWidth] [$l getSpacing] [$l getPitchX] [$l getPitchY] [$l getDirection]] "\t"]
}
close $f
puts "UPPER_LAYER_TOY_NATIVE_STAGES_FINISHED_NOT_SYSTEM_QUALIFICATION"
