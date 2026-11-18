set_thread_count 8
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(C_LIBS) {read_liberty $lib}
read_db $::env(C_FINAL_RES)/6_final.odb
read_sdc $::env(C_FINAL_RES)/6_final.sdc
set_propagated_clock [all_clocks]
source $platform/setRC.tcl
source geometry-all.tcl
geometry_snapshot before-geometry.tsv
set block [ord::get_db_block]
set tech [[ord::get_db] getTech]
set f [open layers.tsv w]
foreach layer [$tech getLayers] {puts $f "[$layer getName]\t[$layer getWidth]"}
close $f
set f [open vias.tsv w]
foreach via [concat [$tech getVias] [$block getVias]] {
 foreach box [$via getBoxes] {puts $f "[$via getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"}
}
close $f
proc master_obstructions {path} {
 set rows {}
 foreach inst [[ord::get_db_block] getInsts] {
  set m [$inst getMaster]
  if {![$m isBlock]} {continue}
  foreach box [$m getObstructions] {lappend rows [join [list [$inst getName] [$m getName] [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]}
 }
 set f [open $path w];puts $f [join [lsort $rows] "\n"];close $f
}
master_obstructions before-master-obs.tsv
write_def before.def
write_db before.odb
# Deliberately no PG precheck: avoid cached checks hiding RCX mutations.
extract_parasitics -ext_model_file $platform/rcx_patterns.rules
write_spef isolated.spef
write_def after.def
write_db after.odb
geometry_snapshot after-geometry.tsv
master_obstructions after-master-obs.tsv
set f [open post-rcx-pg.tsv w]
foreach rail {VDD VSS} {
 set rc [catch {check_power_grid -net $rail} value]
 puts $f "$rail\t$rc\t$value"
 puts "AFTER_RCX_PG $rail CATCH=$rc RESULT=$value"
}
close $f
