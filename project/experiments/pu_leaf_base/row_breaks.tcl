# Isolate standard-cell well rows across each leaf halo boundary.
set block [ord::get_db_block]
set halo [expr {4 * [$block getDbUnitsPerMicron]}]
set limits {}
foreach name $pu_row_macros {
    set macro [$block findInst $name]
    if {$macro eq "NULL"} {error "missing leaf macro $name"}
    set box [$macro getBBox]
    lappend limits [expr {[$box yMin] - $halo}] [expr {[$box yMax] + $halo}]
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
if {[llength $removed] != [llength [lsort -unique $limits]]} {
    error "incomplete leaf well row isolation: $removed at $limits"
}
puts "PU_WELL_ROW_BREAKS $removed"
