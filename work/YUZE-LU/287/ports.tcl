read_db $::env(INPUT_ODB)
set f [open $::env(OUTPUT_TSV) w]
puts $f "port\tdirection\tnet\tinstance\tmaster\tpin\tpin_direction"
foreach b [[ord::get_db_block] getBTerms] {
 set net [$b getNet]
 if {$net eq "NULL"} {continue}
 foreach it [$net getITerms] {
  set inst [$it getInst]
  set mt [$it getMTerm]
  puts $f "[$b getName]\t[$b getIoType]\t[$net getName]\t[$inst getName]\t[[$inst getMaster] getName]\t[$mt getName]\t[$mt getIoType]"
 }
}
close $f
puts PORT_EXPORT_COMPLETE
