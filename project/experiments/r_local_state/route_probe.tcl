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
set selected_ids [dict create]
foreach name $selected {dict set selected_ids $name 1}
set selection_count 0
foreach inst [$block getInsts] {
 if {![regexp {\.(rff|wff)$} [$inst getName]]} {continue}
 incr selection_count
 set pin [$inst findITerm Q]
 if {$pin eq "NULL" || [$pin getNet] eq "NULL"} {error "missing registered selection output"}
 set todo [list [$pin getNet]];set seen [dict create];set endpoints [dict create];set gates [dict create];set max_fanout 0;set hpwl 0
 while {[llength $todo]>0} {
  set net [lindex $todo end];set todo [lrange $todo 0 end-1];set name [$net getName]
  if {[dict exists $seen $name]} {continue};dict set seen $name 1
  if {![dict exists $selected_ids $name]} {dict set selected_ids $name 1;lappend selected $name}
  set fanout 0
  foreach term [$net getITerms] {
   set mt [$term getMTerm]
   if {[$mt getIoType] ne "INPUT"} {continue};incr fanout
   set load [$term getInst];set master [$load getMaster]
   if {[string match "DFF*" [$master getName]]} {dict set endpoints "[$load getName]/[$mt getName]" 1;continue}
   set ln [$load getName]
   if {[dict exists $gates $ln]} {continue};dict set gates $ln 1
   foreach output [$load getITerms] {
    if {[[$output getMTerm] getIoType] eq "OUTPUT" && [$output getNet] ne "NULL"} {lappend todo [$output getNet]}
   }
  }
  if {$fanout>$max_fanout} {set max_fanout $fanout}
 }
 dict for {netname unused} $seen {puts $out "SELECT_NET\t[$inst getName]\t$netname"}
 set endpoint_count [dict size $endpoints]
 puts $out "SELECT\t[$inst getName]\t$endpoint_count\t[dict size $gates]\t[dict size $seen]\t$max_fanout"
 if {$endpoint_count<1 || $endpoint_count>32} {error "physical selection cone endpoint budget failed: [$inst getName] $endpoint_count"}
}
puts $out "SELECTION_SOURCES\t$selection_count"
if {$selection_count==0} {error "no actual local select FFs found"}
foreach name $selected {
 set net [$block findNet $name];set wire [$net getWire]
 set length "unavailable"
 if {$wire ne "NULL"} {catch {set length [$wire getLength]}}
 puts $out "NET\t$name\t$wire\t$length"
 foreach term [$net getITerms] {
  set mt [$term getMTerm];if {[$mt getIoType] eq "OUTPUT"} {continue}
  set inst [$term getInst];lassign [$inst getLocation] x y
  puts $out "LOAD\t$name\t[[$inst getMaster] getName]\t[$mt getName]\t$x\t$y\t[$inst getName]"
 }
}
close $out
