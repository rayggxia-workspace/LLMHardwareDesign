# Explicit physical implementation of the two reset synchronizer constant D's.
# This hook changes no logic value and never removes a connected signal.
set block [ord::get_db_block]
set db [ord::get_db]
set old [$block findNet zero_]
if {$old eq "NULL" || [$old getSigType] ne "GROUND" || [$old isSpecial] || [llength [$old getBTerms]]!=0} {
 error "Unexpected constant net representation"
}
set pins [$old getITerms]
set actual {}
foreach p $pins {
 if {[[$p getMTerm] getIoType] ne "INPUT"} {error "Unexpected constant driver"}
 lappend actual "[[$p getInst] getName]/[[$p getMTerm] getName]"
}
if {[lsort $actual] ne [lsort $expected_zero]} {error "Constant sink mismatch"}
set master [$db findMaster LOGIC0_X1]
if {$master eq "NULL"} {error "Missing tie-low master"}
set f [open [file join [file dirname [info script]] physical-ties.tsv] w]
set index 0
foreach p $pins {
 set target [$p getInst]
 set stem hpy_dm173_tie0_$index
 if {[$block findInst $stem] ne "NULL" || [$block findNet $stem] ne "NULL"} {error "Tie name collision"}
 set inst [odb::dbInst_create $block $master $stem]
 lassign [$target getLocation] x y
 $inst setOrient [$target getOrient]
 $inst setLocation $x $y
 $inst setPlacementStatus PLACED
 set net [odb::dbNet_create $block $stem]
 $net setSigType SIGNAL
 set output [$inst findITerm Z]
 if {$output eq "NULL"} {error "Missing tie output"}
 $output connect $net
 $p disconnect
 $p connect $net
 foreach term [$inst getITerms] {
  set kind [[$term getMTerm] getSigType]
  if {$kind eq "POWER"} {$term connect [$block findNet VDD]}
  if {$kind eq "GROUND"} {$term connect [$block findNet VSS]}
 }
 puts $f "[$target getName]/[[$p getMTerm] getName]\tzero_\tGROUND\t$stem/Z\tSIGNAL\tLOGIC0_X1"
 incr index
}
close $f
if {[llength [$old getITerms]] || [llength [$old getBTerms]]} {error "Constant net still connected"}
odb::dbNet_destroy $old
detailed_placement
check_placement -verbose
puts "PHYSICAL_TIES inserted=$index master=LOGIC0_X1 expected_sinks=$expected_zero"
