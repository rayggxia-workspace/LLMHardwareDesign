# Explicitly release the nets implicated by the frozen actual collision report.
# Called after unchanged fifty-cell sizing/legalization, before rebuilding GRT/AP.
set neighbor_file [open $::env(C_NEIGHBOR_NETS)]
set neighbor_names {}
foreach line [split [read $neighbor_file] "\n"] {
 set line [string trim $line]
 if {$line ne ""} {lappend neighbor_names $line}
}
close $neighbor_file
if {[llength $neighbor_names] != 31 || [llength [lsort -unique $neighbor_names]] != 31} {error "Unexpected frozen conflict-net count"}
set neighbor_block [ord::get_db_block]
set neighbor_log [open neighbor-rip-actual.tsv w]
foreach neighbor_name $neighbor_names {
 set neighbor_net [$neighbor_block findNet $neighbor_name]
 if {$neighbor_net eq "NULL" || [$neighbor_net getSigType] ni {SIGNAL CLOCK}} {error "Invalid literal conflict net $neighbor_name"}
 set neighbor_wire [$neighbor_net getWire]
 puts $neighbor_log "$neighbor_name\t[$neighbor_net getSigType]\t[expr {$neighbor_wire ne "NULL"}]"
 if {$neighbor_wire ne "NULL"} {odb::dbWire_destroy $neighbor_wire}
}
close $neighbor_log
puts RELEASED_FROZEN_31_ACTUAL_CONFLICT_NETS_FOR_STRICT_REROUTING
