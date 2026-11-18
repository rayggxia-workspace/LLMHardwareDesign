set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $::env(C_ECO_SOURCE_ODB)
read_sdc $::env(C_ECO_SOURCE_SDC)
read_spef $root/diagnostics/C-main-v1-rcx/results/6_final.spef
set_propagated_clock [all_clocks]
source $platform/setRC.tcl
source $root/geometry.tcl
geometry_snapshot geometry-original.tsv
source $root/c-freeze-outputs-v1.tcl
freeze_selected_c_outputs
set_dont_use {TAPCELL_X1 FILLCELL_X1 AOI211_X1 OAI211_X1 OAI221_X4}
remove_fillers
repair_design -cap_margin $::env(C_ECO_MARGIN) -slew_margin $::env(C_ECO_MARGIN)
freeze_selected_c_outputs
write_db electric.odb
write_verilog electric.v
puts ACTUAL_PARASITIC_ELECTRICAL_EDIT_ONLY_NOT_SIGNOFF
