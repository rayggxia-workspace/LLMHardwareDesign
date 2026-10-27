# Geometry master must be serialized BEFORE OpenRCX. RCX/STA run on disposable
# analysis state; no post-RCX ODB is promoted as routed geometry.
read_db $::env(PINXY_ODB)
set out $::env(PINXY_FINAL_OUT)
write_db $out/clean.odb
set b [ord::get_db_block];set t [ord::get_db_tech]
set f [open $out/technology.tsv w]
puts $f "dbu_per_um\t[$b getDbUnitsPerMicron]"
puts $f "manufacturing_grid_dbu\t[$t getManufacturingGrid]"
close $f
set f [open $out/pins.tsv w];puts $f "pin\tdirection\tuse\tnet\tlayer\tx0\ty0\tx1\ty1"
foreach p [$b getBTerms] {foreach bp [$p getBPins] {foreach r [$bp getBoxes] {
 puts $f [join [list [$p getName] [$p getIoType] [$p getSigType] [[$p getNet] getName] [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]] "\t"]
}}};close $f
write_def $out/clean.def
write_verilog $out/clean.v
write_abstract_lef $out/abstract.lef
# The export process itself is disposable, too. Do not save DB after checks.
set ::env(PINXY_ACCESS_OUT) $out/selected_access.tsv.gz
source $::env(PINXY_DRIVER)/export_access.tcl
set ::env(PINXY_ACCESS_ALL) 1
set ::env(PINXY_ACCESS_OUT) $out/whole_access.tsv.gz
source $::env(PINXY_DRIVER)/export_access.tcl
puts "CLEAN_GEOMETRY_EXPORTED"
