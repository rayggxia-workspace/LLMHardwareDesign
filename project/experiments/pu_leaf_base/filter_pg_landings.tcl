# Remove only parent-created complete M7-M10 via stacks that approach a leaf signal or upper-layer obstruction.
# Source leaf wires, abstract metal and PG stripes are left intact.
proc pj_bins {lo hi} {
    set bins {}
    for {set i [expr {$lo / 16000}]} {$i <= $hi / 16000} {incr i} {lappend bins $i}
    return $bins
}

proc pj_index_shape {index_var shape layer ox oy guard name} {
    upvar 1 $index_var index
    set l [expr {[$shape xMin]+$ox-$guard}]
    set b [expr {[$shape yMin]+$oy-$guard}]
    set r [expr {[$shape xMax]+$ox+$guard}]
    set t [expr {[$shape yMax]+$oy+$guard}]
    foreach i [pj_bins $l $r] {
        foreach j [pj_bins $b $t] {
            dict lappend index [list $layer $i $j] [list $l $b $r $t $name]
        }
    }
}

proc pj_filter_pg {instances report} {
    set block [ord::get_db_block]
    if {[$block getDbUnitsPerMicron] != 2000} {error "Unexpected PG selection DBU"}
    set guard 3000
    set obstacles [dict create]
    foreach name $instances {
        set inst [$block findInst $name]
        set master [$inst getMaster]
        if {[$inst getOrient] ne "R0" || [$master getOrigin] ne {0 0}} {
            error "PG selection requires R0 and zero master origin"
        }
        lassign [$inst getLocation] ox oy
        foreach term [$master getMTerms] {
            if {[$term getSigType] in {POWER GROUND}} {continue}
            foreach pin [$term getMPins] {
                foreach shape [$pin getGeometry] {
                    set layer [[$shape getTechLayer] getRoutingLevel]
                    if {$layer ni {7 8 9 10}} {continue}
                    pj_index_shape obstacles $shape $layer $ox $oy $guard $name/[$term getName]
                }
            }
        }
        foreach shape [$master getObstructions] {
            set tech [$shape getTechLayer]
            set layer [$tech getRoutingLevel]
            if {$layer in {8 9 10}} {
                pj_index_shape obstacles $shape $layer $ox $oy $guard $name/OBS
            } elseif {[$tech getName] in {via7 via9}} {
                set cut [$tech getName]
                set cut_guard [dict get {via7 880 via9 1760} $cut]
                pj_index_shape obstacles $shape $cut $ox $oy $cut_guard $name/OBS
            }
        }
    }
    set f [open $report w]
    puts $f "supply\tx_dbu\ty_dbu\tmetal\tguard_dbu\tleaf_geometry"
    foreach supply {VDD VSS} {
        set stacks [dict create]
        set hits [dict create]
        foreach wire [[$block findNet $supply] getSWires] {
            foreach box [$wire getWires] {
                if {![$box isVia]} {continue}
                set via [$box getTechVia]
                if {$via eq "NULL"} {set via [$box getBlockVia]}
                set levels {}
                foreach shape [$via getBoxes] {
                    set layer [[$shape getTechLayer] getRoutingLevel]
                    if {$layer} {lappend levels $layer}
                }
                set levels [lsort -integer -unique $levels]
                if {$levels ni {{7 8} {8 9} {9 10}}} {continue}
                set loc [$box getViaXY]
                lassign $loc x y
                dict lappend stacks $loc [list $levels $box]
                foreach shape [$via getBoxes] {
                    set tech [$shape getTechLayer]
                    set layer [$tech getRoutingLevel]
                    if {!$layer} {
                        set layer [$tech getName]
                        if {$layer ni {via7 via9}} {continue}
                    }
                    set l [expr {[$shape xMin]+$x}]
                    set b [expr {[$shape yMin]+$y}]
                    set r [expr {[$shape xMax]+$x}]
                    set t [expr {[$shape yMax]+$y}]
                    foreach i [pj_bins $l $r] {
                        foreach j [pj_bins $b $t] {
                            set key [list $layer $i $j]
                            if {![dict exists $obstacles $key]} {continue}
                            foreach guarded [dict get $obstacles $key] {
                                lassign $guarded pl pb pr pt name
                                if {$l < $pr && $r > $pl && $b < $pt && $t > $pb} {
                                    dict set hits $loc [list $layer $name]
                                }
                            }
                        }
                    }
                }
            }
        }
        dict for {loc hit} $hits {
            set stack [dict get $stacks $loc]
            set kinds [lsort [lmap item $stack {lindex $item 0}]]
            if {$kinds ne {{7 8} {8 9} {9 10}}} {error "Incomplete PG stack at $loc"}
            lassign $loc x y
            lassign $hit layer name
            puts $f "$supply\t$x\t$y\t$layer\t$guard\t$name"
            foreach item $stack {odb::dbSBox_destroy [lindex $item 1]}
        }
        set clean [check_power_grid -net $supply -error_file "$report-$supply.rpt"]
        if {$clean ne "1"} {error "Parent PG connectivity failed for $supply"}
        puts "PJ_PG $supply removed [dict size $hits] complete stacks"
    }
    close $f
}
