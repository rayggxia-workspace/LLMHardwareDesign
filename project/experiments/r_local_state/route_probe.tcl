# Read-only native Tcl probe, supported by the deployed OpenROAD (-Python).
set_thread_count 1
read_db $::env(INPUT_ODB)
set block [ord::get_db_block]
set out [open $::env(OUTPUT_TSV) w]
puts $out "DBU\t[$block getDbUnitsPerMicron]"
set ranks {}
foreach net [$block getNets] {
 if {[$net getSigType] in {POWER GROUND CLOCK}} {continue}
 set count 0
 foreach term [$net getITerms] {if {[[$term getMTerm] getIoType] ne "OUTPUT"} {incr count}}
 if {$count>100} {lappend ranks [list $count [$net getName]]}
}
set selected {}
foreach r [lrange [lsort -integer -decreasing -index 0 $ranks] 0 19] {lappend selected [lindex $r 1]}
foreach name {bank_role role} {if {[$block findNet $name] ne "NULL" && $name ni $selected} {lappend selected $name}}
# Include every local registered row-select source, even when direct fanout is small.
foreach inst [$block getInsts] {
 if {![regexp {\.(rff|wff)$} [$inst getName]]} {continue}
 set pin [$inst findITerm Q]
 if {$pin eq "NULL" || [$pin getNet] eq "NULL"} {error "missing registered selection output"}
 set name [[$pin getNet] getName]
 if {$name ni $selected} {lappend selected $name}
}
foreach name $selected {
 set net [$block findNet $name];set wire [$net getWire]
 set length "unavailable"
 if {$wire ne "NULL"} {catch {set length [$wire getLength]}}
 puts $out "NET\t$name\t$wire\t$length"
 foreach term [$net getITerms] {
  set mt [$term getMTerm];if {[$mt getIoType] eq "OUTPUT"} {continue}
  set inst [$term getInst];lassign [$inst getLocation] x y
  puts $out "LOAD\t$name\t[[$inst getMaster] getName]\t[$mt getName]\t$x\t$y"
 }
}
close $out
