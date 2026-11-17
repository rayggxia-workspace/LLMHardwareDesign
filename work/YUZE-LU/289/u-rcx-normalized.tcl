set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
if {$::env(PROBE_IMPORT) in {odb ordered}} {
 read_db $::env(PROBE_ODB)
 foreach net [[ord::get_db_block] getNets] {
  set rule [$net getNonDefaultRule]
  if {$rule ne "NULL" && [string match i289_upper_v2_* [$rule getName]]} {$net setNonDefaultRule NULL}
 }
} else {
 read_lef $platform/lef/NangateOpenCellLibrary.tech.lef
 read_lef $platform/lef/NangateOpenCellLibrary.macro.mod.lef
 foreach lef $::env(PROBE_LEFS) {read_lef $lef}
 read_def $::env(PROBE_DEF)
}
write_def before.def
write_db before.odb
if {![info exists ::env(PROBE_UNCACHED)]} {
 foreach rail {VDD VSS} {
  set rc [catch {check_power_grid -net $rail} result]
  puts "BEFORE_RCX_PG $rail CATCH=$rc RESULT=$result"
 }
}
extract_parasitics -ext_model_file $platform/rcx_patterns.rules -version $::env(PROBE_RCX_VERSION)
write_spef isolated.spef
write_def after.def
write_db after.odb
foreach rail {VDD VSS} {
 set rc [catch {check_power_grid -net $rail} result]
 puts "AFTER_RCX_PG $rail CATCH=$rc RESULT=$result"
}
