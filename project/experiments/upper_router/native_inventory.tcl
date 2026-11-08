# Read-only ODB inventory for builds without the optional OpenROAD Python API.
read_db $::env(ROUTER_NATIVE_ODB)
set block [ord::get_db_block]
set out [open $::env(ROUTER_INVENTORY_TSV) w]
set die [$block getDieArea]
puts $out [join [list DESIGN [$block getName] [$block getDbUnitsPerMicron] [$die xMin] [$die yMin] [$die xMax] [$die yMax]] "\t"]
foreach term [$block getBTerms] {
    set net [$term getNet]
    if {$net eq "NULL"} {error "unconnected terminal [$term getName]"}
    puts $out [join [list TERM [$term getName] [$term getIoType] [$net getName] [$term getSigType]] "\t"]
    foreach pin [$term getBPins] {
        foreach shape [$pin getBoxes] {
            puts $out [join [list SHAPE [$term getName] [[$shape getTechLayer] getName] [$shape xMin] [$shape yMin] [$shape xMax] [$shape yMax]] "\t"]
        }
    }
    foreach iterm [$net getITerms] {
        set inst [$iterm getInst]
        set mterm [$iterm getMTerm]
        puts $out [join [list OWNER [$term getName] [$mterm getIoType] [$inst getName] [[$inst getMaster] getName] [$mterm getName]] "\t"]
    }
}
foreach inst [$block getInsts] {
    set master [$inst getMaster]
    puts $out [join [list CELL [$master getName]] "\t"]
    if {[$master isBlock]} {
        set b [$inst getBBox]
        puts $out [join [list MACRO [$inst getName] [$master getName] [$inst getOrient] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "\t"]
    }
}
close $out
