# Isolate extraction from the in-memory routing session. Final source stays read-only.
set_thread_count 8
read_db $::env(PROBE_ODB)
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
write_def before.def
extract_parasitics -ext_model_file $platform/rcx_patterns.rules
write_spef isolated.spef
write_def after.def
foreach rail {VDD VSS} {
 set rc [catch {check_power_grid -net $rail} result]
 puts "POST_RCX_PG $rail CATCH=$rc RESULT=$result"
}
