# Isolate an observed well transition, preserving other sites of a split row.
set block [ord::get_db_block]
set requested [dict create]
foreach selection $pu_placed_rows {
    dict set requested [lindex $selection 0] [lrange $selection 1 end]
}
set removed {}
set bounds {}
foreach row [$block getRows] {
    set name [$row getName]
    if {![dict exists $requested $name]} {continue}
    set intervals [dict get $requested $name]
    set box [$row getBBox]
    set y0 [$box yMin]
    set y1 [$box yMax]
    set lo [$box xMin]
    set hi [$box xMax]
    set site [$row getSite]
    set spacing [$row getSpacing]
    set orient [$row getOrient]
    set dir [$row getDirection]
    lassign [$row getOrigin] x y
    set sites [$row getSiteCount]
    lappend removed $name
    odb::dbRow_destroy $row
    if {![llength $intervals]} {
        lappend bounds [list $lo $y0 $hi $y1]
        continue
    }
    if {$x != $lo || $dir ne "HORIZONTAL" || $spacing <= 0} {error "unsupported row $name"}
    set cursor 0
    set piece 0
    foreach {left right} $intervals {
        set start [expr {($left-$x)/$spacing}]
        set stop [expr {($right-$x+$spacing-1)/$spacing}]
        if {$start < $cursor || $stop <= $start || $stop > $sites} {error "invalid gap on $name"}
        if {$start > $cursor} {
            odb::dbRow_create $block "${name}_keep[incr piece]" $site [expr {$x+$cursor*$spacing}] $y \
                $orient $dir [expr {$start-$cursor}] $spacing
        }
        lappend bounds [list [expr {$x+$start*$spacing}] $y0 [expr {$x+$stop*$spacing}] $y1]
        set cursor $stop
    }
    if {$sites > $cursor} {
        odb::dbRow_create $block "${name}_keep[incr piece]" $site [expr {$x+$cursor*$spacing}] $y \
            $orient $dir [expr {$sites-$cursor}] $spacing
    }
}
if {[lsort $removed] ne [lsort [dict keys $requested]]} {error "missing rows for isolation: $removed"}
set taps 0
foreach inst [$block getInsts] {
    set is_tap [expr {[[$inst getMaster] getName] eq "TAPCELL_X1"}]
    if {!$is_tap && ![info exists pu_preserve_active_placement]} {continue}
    set box [$inst getBBox]
    foreach limit $bounds {
        lassign $limit x0 y0 x1 y1
        if {[$box xMin] < $x1 && [$box xMax] > $x0 && [$box yMin] < $y1 && [$box yMax] > $y0} {
            if {!$is_tap} {error "row window overlaps placed cell [$inst getName]"}
            odb::dbInst_destroy $inst
            incr taps
            break
        }
    }
}
puts "PU_WELL_PLACED_ROW_BREAKS $removed windows $bounds taps removed $taps"
if {![info exists pu_preserve_active_placement]} {detailed_placement}
check_placement -verbose
