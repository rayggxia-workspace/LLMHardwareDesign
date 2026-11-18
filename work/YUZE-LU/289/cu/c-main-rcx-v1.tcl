set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(U_LIBS) {read_liberty $lib}
read_db $::env(U_RESULTS)/6_final.odb
read_sdc $::env(U_RESULTS)/6_final.sdc
write_def before-rcx.def
extract_parasitics -ext_model_file $platform/rcx_patterns.rules
write_spef $::env(U_RESULTS)/6_final.spef
write_def after-rcx.def
write_db after-rcx.odb
puts ACTUAL_MAIN_RCX_DIAGNOSTIC_COMPLETE_NATIVE_ONE_NOT_ACCEPTED
