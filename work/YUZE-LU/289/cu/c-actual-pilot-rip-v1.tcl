set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
read_db $root/diagnostics/C-actual-edit-pilot-X8-h50-d50/legalized.odb
proc net_signature {net} {
 set a {}
 foreach it [$net getITerms] {set i [$it getInst];lappend a [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [[$it getMTerm] getName]]}
 foreach bt [$net getBTerms] {lappend a [list BTERM [$bt getName]]}
 return [lsort $a]
}
set f [open $root/diagnostics/C-v27-hold-budget/original-signatures.tcllist];set original [lindex [read $f] 0];close $f
set out [open changed-route-nets.tsv w];set nrip 0
foreach n [[ord::get_db_block] getNets] {
 if {[$n getSigType] in {POWER GROUND}} {continue}
 set name [$n getName]
 if {![dict exists $original $name] || [dict get $original $name] ne [net_signature $n]} {
  set wire [$n getWire]
  if {$wire ne "NULL"} {odb::dbWire_destroy $wire;incr nrip}
  puts $out $name
 }
}
close $out
puts "CHANGED_SIGNAL_ACCESS_REMOVED $nrip"
write_db legal-and-ripped.odb
set f [open pg.tsv w];set bad 0
foreach rail {VDD VSS} {
 set rc [catch {check_power_grid -net $rail} value]
 puts $f "$rail\t$rc\t$value"
 if {$rc || $value ne "1"} {incr bad}
}
close $f
if {$bad} {error "Pre-route PG still contains violations after exact changed-wire ripup"}
puts PRE_ROUTE_PG_PASS_AFTER_STALE_CHANGED_WIRES_REMOVED_NOT_SIGNAL_SIGNOFF
