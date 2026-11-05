# Export real same-net routing rectangles near each M10 signal landing.
read_db $::env(PJ_LEAF_ODB)
set b [ord::get_db_block]
set itr [odb::new_dbWirePathItr]
set path [odb::new_dbWirePath]
set step [odb::new_dbWirePathShape]
set f [open $::env(PJ_LEAF_ROUTES) w]
foreach port [$b getBTerms] {
    if {[$port getSigType] in {POWER GROUND}} {continue}
    set net [$port getNet]
    if {$net eq "NULL"} {continue}
    set wire [$net getWire]
    if {$wire eq "NULL"} {continue}
    set boxes {}
    foreach bp [$port getBPins] {
        foreach box [$bp getBoxes] {
            if {[[$box getTechLayer] getName] eq "metal10"} {lappend boxes $box}
        }
    }
    if {[llength $boxes] != 1} {error "Expected one original M10 landing"}
    set box [lindex $boxes 0]
    odb::dbWirePathItr_begin $itr $wire
    while {[odb::dbWirePathItr_getNextPath $itr $path]} {
        while {[odb::dbWirePathItr_getNextShape $itr $step]} {
            set s [odb::dbWirePathShape_shape_get $step]
            if {![odb::dbShape_isSegment $s]} {continue}
            set layer [odb::dbShape_getTechLayer $s]
            set name [$layer getName]
            if {$name ni {metal8 metal9 metal10}} {continue}
            set x0 [odb::dbShape_xMin $s]
            set x1 [odb::dbShape_xMax $s]
            set y0 [odb::dbShape_yMin $s]
            set y1 [odb::dbShape_yMax $s]
            # Clip the real wire box to the local access window. Never add metal.
            set x0 [expr {max($x0, [$box xMin]-24000)}]
            set y0 [expr {max($y0, [$box yMin]-24000)}]
            set x1 [expr {min($x1, [$box xMax]+24000)}]
            set y1 [expr {min($y1, [$box yMax]+24000)}]
            if {$x0 >= $x1 || $y0 >= $y1} {continue}
            puts $f "[$port getName]\t$name\t$x0 $y0 $x1 $y1"
        }
    }
}
close $f
odb::delete_dbWirePathShape $step
odb::delete_dbWirePath $path
odb::delete_dbWirePathItr $itr
