# Add real parent M10 rectangles across diagnosed notches of a single net.
read_db $::env(PU_NOTCH_INPUT)
set block [ord::get_db_block]
if {[$block getDbUnitsPerMicron] != 2000} {error "unexpected native database units"}
if {$::env(PU_FINAL_ROW_WINDOWS) ne ""} {
    set handle [open $::env(PU_FINAL_ROW_WINDOWS) r]
    set pu_placed_rows [split [string trim [read $handle]] "\n"]
    close $handle
    foreach row $pu_placed_rows {
        if {![regexp {^ROW_[0-9_]+( [0-9]+ [0-9]+)+$} $row]} {error "invalid routed well window: $row"}
    }
    set pu_preserve_active_placement 1
    remove_fillers
    source [file join [file dirname [info script]] isolate_placed_rows.tcl]
    filler_placement {FILLCELL_X1 FILLCELL_X2 FILLCELL_X4 FILLCELL_X8 FILLCELL_X16 FILLCELL_X32}
}
if {$::env(PU_FINAL_PG_REMOVAL) ne ""} {
    source [file join [file dirname [info script]] remove_parent_pg_stack.tcl]
}
set layer [[ord::get_db_tech] findLayer metal10]
set itr [odb::new_dbWirePathItr]
set path [odb::new_dbWirePath]
set step [odb::new_dbWirePathShape]
set encoder [odb::dbWireEncoder]
set patches [open $::env(PU_NOTCH_PATCHES) r]
while {[gets $patches line] >= 0} {
    lassign [split $line "\t"] net_name leaf port x0 y0 x1 y1
    if {[llength [split $line "\t"]] != 7 || !($x0 < $x1 && $y0 < $y1)} {
        error "invalid M10 notch row: $line"
    }
    set net [$block findNet $net_name]
    if {$net eq "NULL" || [$net getSigType] ne "SIGNAL"} {error "invalid notch net $net_name"}
    if {$leaf ne "-"} {
        set inst [$block findInst $leaf]
        if {$inst eq "NULL" || ![[$inst getMaster] isBlock]} {error "invalid leaf $leaf"}
        set term [$inst findITerm $port]
        if {$term eq "NULL" || [$term getNet] ne $net} {error "net does not bind to $leaf/$port"}
    }
    set wire [$net getWire]
    if {$wire eq "NULL"} {error "unrouted notch net $net_name"}
    set touching 0
    odb::dbWirePathItr_begin $itr $wire
    while {[odb::dbWirePathItr_getNextPath $itr $path]} {
        while {[odb::dbWirePathItr_getNextShape $itr $step]} {
            set shape [odb::dbWirePathShape_shape_get $step]
            if {![odb::dbShape_isSegment $shape] || [odb::dbShape_getTechLayer $shape] ne $layer} {continue}
            if {[odb::dbShape_xMin $shape] < $x1 && [odb::dbShape_xMax $shape] > $x0 &&
                [odb::dbShape_yMin $shape] < $y1 && [odb::dbShape_yMax $shape] > $y0} {incr touching}
        }
    }
    if {$touching < ($leaf eq "-" ? 2 : 1)} {error "no matching routed M10 copper for $line"}
    set x [expr {($x0+$x1)/2}]
    set y [expr {($y0+$y1)/2}]
    $encoder append $wire
    $encoder newPath $layer ROUTED
    $encoder addPoint $x $y
    $encoder addRect [expr {$x0-$x}] [expr {$y0-$y}] [expr {$x1-$x}] [expr {$y1-$y}]
    $encoder end
    puts "PU_NATIVE_NOTCH $line"
}
close $patches
write_db $::env(PU_NOTCH_OUTPUT)
