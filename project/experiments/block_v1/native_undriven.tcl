# A connected dbNet is insufficient: every used signal needs a real source.
set bv1_stream [open $::env(BV1_UNDRIVEN_REPORT) w]
set bv1_bad 0
set bv1_used 0
foreach net [[ord::get_db_block] getNets] {
  if {[$net getSigType] in {POWER GROUND}} {continue}
  set readers 0
  set drivers 0
  foreach term [$net getITerms] {
    set mt [$term getMTerm]
    if {[$mt getSigType] in {POWER GROUND}} {continue}
    if {[$mt getIoType] in {INPUT INOUT}} {incr readers}
    if {[$mt getIoType] in {OUTPUT INOUT}} {incr drivers}
  }
  set ports {}
  foreach port [$net getBTerms] {
    if {[$port getIoType] in {INPUT INOUT}} {incr drivers}
    if {[$port getIoType] in {OUTPUT INOUT}} {incr readers}
    lappend ports [$port getName]
  }
  if {$readers>0} {incr bv1_used}
  if {$readers>0 && $drivers==0} {
    incr bv1_bad
    puts $bv1_stream "UNDRIVEN\t[$net getName]\t$readers\t[join $ports ,]"
  }
}
puts $bv1_stream "SUMMARY\t$bv1_used\t$bv1_bad"
close $bv1_stream
