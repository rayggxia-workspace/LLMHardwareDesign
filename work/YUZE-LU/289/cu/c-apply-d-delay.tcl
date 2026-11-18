read_db unshared.odb
source delay-plan.tcl
set b [ord::get_db_block]
set cells [dict create]
foreach i [$b getInsts] {dict set cells [string map [list "\\" ""] [$i getName]] $i}
set master [[ord::get_db] findMaster CLKBUF_X1]
set serial 0
foreach spec $delay_plan {
 lassign $spec full count
 set full [string map [list "\\" ""] $full]
 set slash [string last / $full]
 set name [string range $full 0 [expr {$slash-1}]]
 set term [string range $full [expr {$slash+1}] end]
 if {$term ne "D" || ![dict exists $cells $name]} {error "Expected exact ordinary state D endpoint $full"}
 set si [dict get $cells $name]
 if {![string match DFF* [[$si getMaster] getName]]} {error "Non-DFF endpoint $full"}
 set sink [$si findITerm D]
 set prev [$sink getNet]
 $sink disconnect
 lassign [$si getLocation] x y
 for {set j 0} {$j<$count} {incr j} {
  set n i289_donly_${serial}_$j
  set i [odb::dbInst_create $b $master $n]
  $i setLocation $x $y
  $i setPlacementStatus PLACED
  set net [odb::dbNet_create $b ${n}_net]
  [$i findITerm A] connect $prev
  [$i findITerm Z] connect $net
  set prev $net
 }
 $sink connect $prev
 incr serial
}
puts "D_BRANCHES_DELAYED $serial"
write_db delayed.odb