# Routing-only guard derived from independent M10 tip and PG spacing markers.
set block [ord::get_db_block]
if {[$block getDbUnitsPerMicron] != 2000} {error "unexpected M10 database units"}
set layer [[ord::get_db_tech] findLayer metal10]
set eol [odb::dbTechLayerSpacingRule_create $layer]
$eol setSpacing 1800
$eol setEol 1700 2000 0 0 0 0
set halo [expr {round($pu_m10_guard_um * 2000)}]
set guards [dict create]
if {$halo > 0} {
    set die [$block getDieArea]
    foreach supply {VDD VSS} {
        foreach swire [[$block findNet $supply] getSWires] {
            foreach shape [$swire getWires] {
                set boxes [list $shape]
                set x 0
                set y 0
                if {[$shape isVia]} {
                    set via [$shape getTechVia]
                    if {$via eq "NULL"} {set via [$shape getBlockVia]}
                    set boxes [$via getBoxes]
                    lassign [$shape getViaXY] x y
                }
                foreach box $boxes {
                    if {[[$box getTechLayer] getName] ne "metal10"} {continue}
                    set x0 [expr {max([$die xMin], [$box xMin] + $x - $halo)}]
                    set y0 [expr {max([$die yMin], [$box yMin] + $y - $halo)}]
                    set x1 [expr {min([$die xMax], [$box xMax] + $x + $halo)}]
                    set y1 [expr {min([$die yMax], [$box yMax] + $y + $halo)}]
                    dict set guards [list $x0 $y0 $x1 $y1] 1
                }
            }
        }
    }
    if {[dict size $guards] == 0} {error "no parent M10 power shape to guard"}
    foreach coords [dict keys $guards] {
        set shadow [odb::dbObstruction_create $block $layer {*}$coords]
        odb::dbBoolProperty_create $shadow pu_m10_route_shadow 1
    }
}
puts "PU_M10_GUARD: EOL 0.900 um up to width 0.850 um, parent PG halo $pu_m10_guard_um um, rectangles [dict size $guards]"
