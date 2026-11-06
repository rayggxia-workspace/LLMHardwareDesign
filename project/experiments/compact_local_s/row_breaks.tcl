# Leave one empty standard-cell row where a bank halo changes row width.
# Otherwise adjacent wells from a full and a shortened row share an abrupt
# corner. The empty row is physical separation, and no GDS patch is needed.
set block [ord::get_db_block]
set limits {}
foreach inst [$block getInsts] {
    if {[[$inst getMaster] getName] eq "s_sram_256x128_freepdk45"} {
        set bank [$inst getBBox]
        set halo [expr {4 * [$block getDbUnitsPerMicron]}]
        lappend limits [expr {[$bank yMin] - $halo}] [expr {[$bank yMax] + $halo}]
    }
}
set removed {}
foreach row [$block getRows] {
    set box [$row getBBox]
    foreach y $limits {
        if {[$box yMin] <= $y && $y < [$box yMax]} {
            lappend removed [$row getName]
            odb::dbRow_destroy $row
            break
        }
    }
}
if {[llength $removed] != 4} {error "Expected four row transitions, got $removed"}
puts "COMPACT_S_WELL_ROW_BREAKS $removed"
