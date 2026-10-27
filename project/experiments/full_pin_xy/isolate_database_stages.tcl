# Diagnose serialization/analysis/export side effects without modifying inputs.
set out $::env(PINXY_ISOLATION_OUT)
proc checkpoint {stage} {
  global out
  write_db $out/$stage.odb
  set f [open $out/$stage.tech.tsv w]
  foreach l [[ord::get_db_tech] getLayers] {puts $f [list [$l getName] [$l getWidth] [$l getSpacing] [$l getPitchX] [$l getPitchY]]};close $f
  set ::env(PINXY_ACCESS_OUT) $out/$stage.access.tsv
  if {[catch {source $::env(PINXY_DRIVER)/export_access.tcl} message]} {puts "ACCESS_EXPORT_FAIL $stage $message"}
  puts "ISOLATION_CHECKPOINT $stage"
}
if {$::env(PINXY_ISOLATION_MODE) eq "NO_LIB"} {
  read_db $::env(PINXY_ODB);checkpoint db_only;exit
}
source $::env(PINXY_LIBS_TCL)
read_db $::env(PINXY_ODB)
checkpoint loaded
read_sdc $::env(PINXY_SDC)
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
set_routing_layers -signal metal2-metal10 -clock metal4-metal10
checkpoint constrained
define_process_corner -ext_model_index 0 X
set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules
extract_parasitics
write_spef $out/extracted.spef
checkpoint extracted
read_spef $out/extracted.spef
checkpoint spef_read
drt::check_drc -output_file $out/in_memory.drc
checkpoint drc_checked
write_abstract_lef $out/abstract.lef
checkpoint abstract_written
