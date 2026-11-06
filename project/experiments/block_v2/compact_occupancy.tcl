read_db $::env(COMPACT_ODB)
set block [ord::get_db_block]
proc box_row {label box} {
    puts [join [list $label [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]
}
puts "dbu\t[$block getDbUnitsPerMicron]"
box_row die [$block getDieArea]
box_row core [$block getCoreArea]
foreach inst [$block getInsts] {
    set master [$inst getMaster]
    set type [$master getType]
    set signal 0
    foreach term [$master getMTerms] {
        if {[$term getSigType] in {SIGNAL CLOCK}} {set signal 1; break}
    }
    if {$signal && $type ni {CORE_SPACER CORE_WELLTAP CORE_ANTENNACELL}} {
        box_row active [$inst getBBox]
    }
}
