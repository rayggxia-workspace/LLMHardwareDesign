# Fresh process: read actual exported timing model and physical abstract.
read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef
read_lef cfj_group_c_memory_legacy.lef
read_liberty cfj_group_c_memory_legacy.lib
set cells [get_lib_cells *]
if {[llength $cells]!=1} {error "Unexpected timing model cell count"}
set f [open imported-timing-cell.txt w];puts $f [get_full_name [lindex $cells 0]];close $f
report_units
set m [[ord::get_db] findMaster cfj_group_c_memory_legacy]
if {$m eq "NULL"} {error "Exported LEF master did not import"}
set f [open imported-pins.tsv w]
puts $f "SIZE\t[$m getWidth]\t[$m getHeight]"
foreach t [$m getMTerms] {
 puts $f "TERM\t[$t getName]\t[$t getIoType]\t[$t getSigType]"
 foreach p [$t getMPins] {foreach b [$p getGeometry] {
  puts $f "PIN\t[$t getName]\t[[$b getTechLayer] getName]\t[$b xMin]\t[$b yMin]\t[$b xMax]\t[$b yMax]"
 }}
}
close $f
puts INDEPENDENT_MODEL_LIBERTY_AND_LEF_IMPORTED
