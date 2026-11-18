# Native-width rule isolation for extraction; physical source remains unmodified.
set_thread_count 8
read_db $::env(PROBE_ODB)
set block [ord::get_db_block]
set changed 0
foreach net [$block getNets] {
 set rule [$net getNonDefaultRule]
 if {$rule eq "NULL" || ![string match i289_upper_v2_* [$rule getName]]} {continue}
 foreach layer [[ord::get_db_tech] getLayers] {
  if {[$layer getType] ne "ROUTING"} {continue}
  set lr [$rule getLayerRule $layer]
  if {$lr eq "NULL" || [$lr getWidth] != [$layer getWidth]} {error "Non-native wire width"}
 }
 $net setNonDefaultRule NULL
 incr changed
}
if {$changed != 8} {error "Unexpected candidate source rule count $changed"}
extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules
write_spef isolated.spef
write_db reordered.odb
write_def reordered.def
# No earlier check_power_grid invocation can cache grid objects in this process.
foreach rail {VDD VSS} {
 set rc [catch {check_power_grid -net $rail} result]
 puts "POST_RCX_UNCACHED_PG $rail CATCH=$rc RESULT=$result"
}
