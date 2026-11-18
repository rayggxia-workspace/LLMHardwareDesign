set_thread_count 8
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v40-final-sizes/regenerated-ap.odb
set b [ord::get_db_block]
set f [open all-nets.txt];set o [open literal-db-net-validation.tsv w];set count 0
while {[gets $f name]>=0} {
 if {$name eq ""} {continue}
 set n [$b findNet $name];if {$n eq "NULL"} {error "Missing exact literal net $name"}
 set type [$n getSigType];set wired [expr {[$n getWire] ne "NULL"}]
 set rows {}
 foreach it [$n getITerms] {lappend rows [list [[$it getInst] getName] [[$it getMTerm] getName]]}
 foreach bt [$n getBTerms] {lappend rows [list PIN [$bt getName]]}
 puts $o [join [list $name $type $wired [llength $rows] [lsort $rows]] "\t"]
 if {$type in {POWER GROUND}} {error "PG net unexpectedly in signal marker plan $name"}
 incr count
}
close $f;close $o;puts "LITERAL_NET_VALIDATION_COMPLETE $count"
