set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db edited.odb
read_sdc $root/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.sdc
source $root/c-freeze-outputs-v1.tcl
freeze_selected_c_outputs
help detailed_placement > dpl-help.txt
detailed_placement -max_displacement {50 50}
check_placement -verbose
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
source $root/geometry.tcl
geometry_snapshot geometry-after-legal.tsv
exec cmp geometry-original.tsv geometry-after-legal.tsv
write_db legalized.odb
write_verilog legalized.v
set f [open pg.tsv w]
foreach rail {VDD VSS} {set val [check_power_grid -net $rail];puts $f "$rail\t$val";if {$val ne "1"} {error "PG failed"}}
close $f
puts ACTUAL_EDIT_LEGAL_PILOT_PASS_NOT_ROUTED_NOT_ACCEPTED
