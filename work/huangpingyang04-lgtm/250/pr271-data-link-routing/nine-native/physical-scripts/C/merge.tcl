read_db full-native.odb
proc connectivity {} {
 set rows {}
 foreach n [[ord::get_db_block] getNets] {
  set pins {}
  foreach t [$n getITerms] {lappend pins [list I [[$t getInst] getName] [[$t getMTerm] getName]]}
  foreach t [$n getBTerms] {lappend pins [list B [$t getName]]}
  lappend rows [list [$n getName] [lsort $pins]]
 }
 return [lsort $rows]
}
set before [connectivity]
read_def -incremental routed-subset.def
if {$before ne [connectivity]} {error "Native netlist changed during selected-route merge"}
write_db native-final.odb
write_def native-final.def
set f [open merge-receipt.txt w]
puts $f "PASS: complete native netlist preserved exactly across selected-route DEF merge"
puts $f "native_nets [llength $before]"
close $f
