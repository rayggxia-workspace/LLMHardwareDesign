# Keep one empty standard-cell row at each leaf halo transition to separate
# the well corners at the boundary between continuous and fragmented rows.
set block [ord::get_db_block]
set halo [expr {2 * [$block getDbUnitsPerMicron]}]
set transitions {}
foreach inst [$block getInsts] {
    if {![[$inst getMaster] isBlock]} {continue}
    set box [$inst getBBox]
    lappend transitions [expr {[$box yMin] - $halo}] [expr {[$box yMax] + $halo}]
}
set removed {}
foreach row [$block getRows] {
    set box [$row getBBox]
    foreach y $transitions {
        if {[$box yMin] <= $y && $y < [$box yMax]} {
            lappend removed [$row getName]
            odb::dbRow_destroy $row
            break
        }
    }
}
if {![llength $removed]} {error "No CFJ well row breaks installed"}
puts "CFJ_WELL_ROW_BREAKS $removed"
tapcell -distance 120 -tapcell_master $::env(TAP_CELL_NAME) -endcap_master $::env(TAP_CELL_NAME) \
    -halo_width_x 2 -halo_width_y 2 -disallow_one_site_gaps
