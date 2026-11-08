# Prefabrication repair for the pinned C TX-slot source/CTS snapshot.
# OAI221_X4 alone fails native METAL1.5; the original X2 master passes.
# Replace standard-cell logic, never edit native cell geometry or waive DRC.
set block [ord::get_db_block]
set inst [$block findInst _57974_]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne "OAI221_X4"} {error "Pinned OAI221_X4 identity changed"}
proc capture_pins {inst} {
    set pairs {}
    foreach term [$inst getITerms] {
        set net [$term getNet]
        lappend pairs [list [[$term getMTerm] getName] [expr {$net eq "NULL" ? "NULL" : [$net getName]}]]
    }
    return [lsort $pairs]
}
set pins [capture_pins $inst]
set location [$inst getLocation]
if {[replace_cell [get_cells _57974_] OAI221_X2]!=1} {error "Equivalent OAI221_X2 replacement rejected"}
if {[capture_pins $inst] ne $pins || [$inst getLocation] ne $location || [[$inst getMaster] getName] ne "OAI221_X2"} {error "Resize changed connectivity or location"}
set_dont_use [get_lib_cells */OAI221_X4]
set_dont_touch [get_cells _57974_]
global_connect
check_placement -verbose
set audit [open $::env(RESULTS_DIR)/c-oai221-repair.tsv w]
puts $audit "_57974_\tOAI221_X4\tOAI221_X2\t$location\t$pins"
close $audit
puts "C_OAI221_REPAIR X4_to_X2 location_and_connections_preserved"
