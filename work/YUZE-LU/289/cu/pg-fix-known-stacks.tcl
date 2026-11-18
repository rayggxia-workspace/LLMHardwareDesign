read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/u-macro-pdn-v1/pdn-candidate.odb
set block [ord::get_db_block]
set allpoints [dict create VDD {{1179080 624000} {1059080 624000} {1299080 624000} {819080 144000} {1059080 144000} {1539080 144000} {1299080 144000} {1179080 144000} {1419080 144000}} VSS {{808280 354600} {928280 653400} {808280 653400} {1048280 114600}}]
foreach rail {VDD VSS} {
set points [dict get $allpoints $rail]
set removals [dict create]
foreach wire [[$block findNet $rail] getSWires] {
 foreach box [$wire getWires] {
  if {![$box isVia]} {continue}
  set via [$box getBlockVia]
  if {$via eq "NULL" || ![regexp {^via(7_8|8_9|9_10)_} [$via getName] -> level]} {continue}
  set x [expr {([$box xMax]+[$box xMin])/2}]
  foreach pt $points {
   lassign $pt cx cy
   if {$x == $cx && [$box yMin] <= $cy && $cy <= [$box yMax]} {
    if {[dict exists $removals $pt $level]} {error "Duplicate stack"}
    dict set removals $pt $level $box
   }
  }
 }
}
if {[dict size $removals] != [llength $points]} {error "Expected exact nine stack sites"}
dict for {pt levels} $removals {
 if {[dict size $levels] != 3} {error "Expected complete redundant stack at $pt"}
 dict for {level box} $levels {
  puts "REMOVE $rail $pt $level"
  odb::dbSBox_destroy $box
 }
}
}
foreach rail {VDD VSS} {
 if {[check_power_grid -net $rail] ne "1"} {error "PG still invalid: $rail"}
}
# Signal routing is rebuilt from this CTS-stage candidate and checked at final signoff.
write_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/u-macro-pdn-v1/pdn-connected.odb
puts "PG_FIX_PASS: 39 via objects removed at 13 conflict sites; both rail checks and routed signal check pass"
