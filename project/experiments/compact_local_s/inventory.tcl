read_db $::env(COMPACT_ODB)
set block [ord::get_db_block]
set units [$block getDbUnitsPerMicron]
set f [open "$::env(COMPACT_OUT).cells.tsv" w]
set die [$block getDieArea]
puts $f [join [list $units [$die xMin] [$die yMin] [$die xMax] [$die yMax]] "\t"]
foreach inst [$block getInsts] {
    if {[$inst getPlacementStatus] in {NONE UNPLACED}} {continue}
    set master [$inst getMaster]
    set box [$inst getBBox]
    puts $f [join [list [$master getName] [$master getType] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]
}
close $f
set f [open "$::env(COMPACT_OUT).pins.tsv" w]
foreach term [$block getBTerms] {
    if {[$term getSigType] in {POWER GROUND}} {continue}
    foreach pin [$term getBPins] {
        foreach box [$pin getBoxes] {
            puts $f [join [list [$term getName] [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]
        }
    }
}
close $f
exit
