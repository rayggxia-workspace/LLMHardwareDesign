exec sha256sum /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib > standard-library.sha256
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(U_LIBS) {read_liberty $lib}
read_db $::env(U_FINAL_RES)/6_final.odb
read_sdc $::env(U_FINAL_RES)/6_final.sdc
read_spef $::env(U_FINAL_RES)/6_final.spef
set_propagated_clock [all_clocks]
sta::find_timing
set bad [expr {[sta::endpoint_violation_count max]+[sta::endpoint_violation_count min]}]
foreach kind {capacitance slew fanout} {incr bad [sta::max_${kind}_violation_count]}
if {$bad} {error "Cannot export accepted model with $bad timing/electrical violations"}
report_check_types -recovery -removal -violators -verbose -digits 9 > model-async.rpt
set f [open model-async.rpt];set async [read $f];close $f
if {[regexp -nocase {VIOLATED} $async]} {error "Cannot export model with async violation"}
write_timing_model -library_name u_n32_controlled_dma_64_x8_tt -cell_name u_n32_controlled_dma_64 u_n32_controlled_dma_64.lib
write_abstract_lef -bloat_factor 0 u_n32_controlled_dma_64.lef
write_sdc -digits 9 model-sdc-readback.sdc
report_units
puts FINAL_U_MODEL_EXPORT_FINISHED_NOT_RELEASE_ACCEPTANCE
