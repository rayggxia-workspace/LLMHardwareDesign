# Read-only: no placement locking, resizing, routing or database writes.
read_db $::env(C_AUDIT_ODB)
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-final-v1/geometry-all.tcl
geometry_snapshot $::env(C_AUDIT_GEOMETRY)
if {$::env(C_AUDIT_DRIVERS) ne "1"} {exit}
set b [ord::get_db_block]
set f [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/C-outputs.txt]
set o [open drivers.tsv w];set count 0;set seen {}
while {[gets $f port]>=0} {
 if {$port eq ""} {continue}
 if {$port in $seen} {error "Duplicate selected output $port"};lappend seen $port
 set bt [$b findBTerm $port]
 if {$bt eq "NULL" || [$bt getIoType] ne "OUTPUT"} {error "Missing selected output $port"}
 set drivers {}
 foreach it [[$bt getNet] getITerms] {if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $it}}
 if {[llength $drivers]!=1} {error "Selected driver cardinality $port"}
 set it [lindex $drivers 0];set inst [$it getInst];set master [[$inst getMaster] getName]
 if {$master ne "BUF_X8"} {error "Expected BUF_X8 at $port, found $master"}
 puts $o [join [list $port [[$bt getNet] getName] [$inst getName] $master [[$it getMTerm] getName]] "\t"]
 incr count
}
close $f;close $o
if {$count!=153} {error "Expected 153 unique selected outputs"}
